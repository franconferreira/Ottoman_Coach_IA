"""Extractor de Características Acústicas y Tímbricas (Feature Engineering).

Extrae un vector unificado de 34 features por audio:
- Prosodia: F0 (media, mediana, std, min, max), Energía RMS, Ataque de energía, Ratio de pausas, WPM estimado.
- Espectro: Centroide espectral, Rolloff espectral, Zero-Crossing Rate (ZCR).
- Timbre (Tracto Vocal / Biometría): 13 Coeficientes Mel-Frequency Cepstral (MFCCs) + Deltas.

Funciona con numpy y scipy (sin requerir librosa) para máxima portabilidad y velocidad.
"""

from __future__ import annotations

import math
import wave
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
from scipy import signal
from scipy.fftpack import dct


class ExtractorAcusticoRobusto:
    """Extrae vectores de features acústicos para SER (emociones) y Biometría (locutor)."""

    NOMBRES_FEATURES = [
        # Prosodia básica (7)
        "f0_media",
        "f0_mediana",
        "f0_std",
        "f0_min",
        "f0_max",
        "volumen_rms_db",
        "ataque_energia",
        "ratio_pausas",
        "rapidez_wpm_est",
        # Espectro y dinámicas (3)
        "zcr_media",
        "centroide_espectral_hz",
        "rolloff_espectral_hz",
        # MFCCs 1 a 13 (13) - Huella tímbrica
        *(f"mfcc_{i+1}" for i in range(13)),
        # Deltas MFCCs 1 a 9 (9) - Dinámica temporal del timbre
        *(f"mfcc_delta_{i+1}" for i in range(9)),
    ]

    def __init__(self, sample_rate_esperado: int = 16000, n_mfcc: int = 13, n_filtros_mel: int = 26):
        self.sample_rate = sample_rate_esperado
        self.n_mfcc = n_mfcc
        self.n_filtros_mel = n_filtros_mel
        self._banco_filtros_mel = self._crear_banco_filtros_mel()

    def _hz_a_mel(self, hz: float) -> float:
        return 2595.0 * math.log10(1.0 + hz / 700.0)

    def _mel_a_hz(self, mel: float) -> float:
        return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)

    def _crear_banco_filtros_mel(self, n_fft: int = 512) -> np.ndarray:
        """Construye matriz de filtros triangulares Mel."""
        f_min = 50.0
        f_max = self.sample_rate / 2.0
        mel_min = self._hz_a_mel(f_min)
        mel_max = self._hz_a_mel(f_max)
        puntos_mel = np.linspace(mel_min, mel_max, self.n_filtros_mel + 2)
        puntos_hz = [self._mel_a_hz(m) for m in puntos_mel]
        bins = np.floor((n_fft + 1) * np.array(puntos_hz) / self.sample_rate).astype(int)

        banco = np.zeros((self.n_filtros_mel, int(n_fft // 2 + 1)), dtype=np.float32)
        for m in range(1, self.n_filtros_mel + 1):
            f_m_minus = bins[m - 1]
            f_m = bins[m]
            f_m_plus = bins[m + 1]

            for k in range(f_m_minus, f_m):
                if f_m != f_m_minus:
                    banco[m - 1, k] = (k - bins[m - 1]) / (bins[m] - bins[m - 1])
            for k in range(f_m, f_m_plus):
                if f_m_plus != f_m:
                    banco[m - 1, k] = (bins[m + 1] - k) / (bins[m + 1] - bins[m])

        return banco

    def _estimar_f0_autocorrelacion(
        self, tramo: np.ndarray, sr: int, fmin: float = 65.0, fmax: float = 380.0
    ) -> Optional[float]:
        """Estima la frecuencia fundamental F0 en un cuadro de audio vía autocorrelación."""
        if len(tramo) < 64:
            return None
        # Enfatizar formantes y quitar componente DC
        tramo_centrado = tramo - np.mean(tramo)
        var = np.var(tramo_centrado)
        if var < 1e-5:
            return None

        corr = signal.correlate(tramo_centrado, tramo_centrado, mode="full")
        corr = corr[len(corr) // 2 :]

        lag_min = int(sr / fmax)
        lag_max = int(sr / fmin)
        if lag_max >= len(corr):
            lag_max = len(corr) - 1
        if lag_min >= lag_max:
            return None

        segmento = corr[lag_min:lag_max]
        if len(segmento) == 0:
            return None

        pico_rel = int(np.argmax(segmento))
        pico = lag_min + pico_rel
        if corr[0] > 0 and (corr[pico] / corr[0]) >= 0.28:
            return float(sr / pico)
        return None

    def extraer_desde_audio(
        self,
        audio_norm: np.ndarray,
        sample_rate: int = 16000,
        texto_opcional: str = "",
    ) -> np.ndarray:
        """Procesa una señal de audio (array float32 en [-1.0, 1.0]) y devuelve un vector de 34 features."""
        if len(audio_norm) < 512:
            return np.zeros(len(self.NOMBRES_FEATURES), dtype=np.float32)

        sr = sample_rate
        # Cuadros de 30ms con solapamiento de 15ms
        frame_len = int(sr * 0.030)
        hop_len = int(sr * 0.015)
        n_frames = max(1, (len(audio_norm) - frame_len) // hop_len + 1)

        f0_lista: List[float] = []
        rms_lista: List[float] = []
        zcr_lista: List[float] = []
        mfcc_frames: List[np.ndarray] = []
        centroides: List[float] = []
        rolloffs: List[float] = []

        ventana = np.hanning(frame_len)
        fft_bins = 512
        freqs = np.linspace(0, sr / 2.0, fft_bins // 2 + 1)

        for i in range(n_frames):
            inicio = i * hop_len
            cuadro = audio_norm[inicio : inicio + frame_len]
            if len(cuadro) < frame_len:
                cuadro = np.pad(cuadro, (0, frame_len - len(cuadro)))

            # 1. RMS y ZCR
            rms = float(np.sqrt(np.mean(cuadro**2)))
            rms_lista.append(rms)
            zcr = float(np.mean(np.abs(np.diff(np.signbit(cuadro)))))
            zcr_lista.append(zcr)

            # 2. F0 si el cuadro tiene energía
            if rms > 0.015:
                f0 = self._estimar_f0_autocorrelacion(cuadro, sr)
                if f0:
                    f0_lista.append(f0)

            # 3. FFT y Espectro
            cuadro_win = cuadro * ventana
            fft_mag = np.abs(np.fft.rfft(cuadro_win, n=512))
            fft_power = (fft_mag**2) / 512.0

            # Centroide espectral
            suma_power = np.sum(fft_power)
            if suma_power > 1e-7:
                c_esp = float(np.sum(freqs * fft_power) / suma_power)
                centroides.append(c_esp)

                # Spectral Rolloff (85% de la energía)
                acum = np.cumsum(fft_power)
                idx_85 = np.searchsorted(acum, 0.85 * suma_power)
                rolloffs.append(float(freqs[min(idx_85, len(freqs) - 1)]))

            # 4. MFCCs por banco Mel
            energia_mel = np.dot(self._banco_filtros_mel, fft_power)
            energia_mel = np.where(energia_mel == 0, np.finfo(float).eps, energia_mel)
            log_mel = np.log(energia_mel)
            mfcc_cuadro = dct(log_mel, type=2, norm="ortho")[: self.n_mfcc]
            mfcc_frames.append(mfcc_cuadro)

        # Agregación temporal de métricas
        rms_arr = np.array(rms_lista, dtype=np.float32)
        piso_ruido = float(np.percentile(rms_arr, 15)) if len(rms_arr) else 0.01
        umbral_vad = max(0.012, piso_ruido * 2.0)
        activos = rms_arr >= umbral_vad

        # F0 estadísticas
        if f0_lista:
            f0_arr = np.array(f0_lista, dtype=np.float32)
            f0_media = float(np.mean(f0_arr))
            f0_mediana = float(np.median(f0_arr))
            f0_std = float(np.std(f0_arr))
            f0_min = float(np.min(f0_arr))
            f0_max = float(np.max(f0_arr))
        else:
            f0_media = f0_mediana = 150.0
            f0_std = 12.0
            f0_min = 120.0
            f0_max = 180.0

        # Volumen RMS en dB
        rms_voz = float(np.mean(rms_arr[activos])) if np.any(activos) else float(np.mean(rms_arr) if len(rms_arr) else 0.01)
        volumen_db = float(np.clip(20.0 * math.log10(max(rms_voz, 1e-4)), -55.0, 0.0))

        # Ataque de energía
        diffs_pos = np.maximum(0.0, np.diff(rms_arr))
        ataque_energia = (
            float(np.clip(np.percentile(diffs_pos, 90) * 8.5, 0.0, 1.0)) if diffs_pos.size else 0.25
        )

        # Ratio de pausas y WPM
        indices_activos = np.where(activos)[0]
        if indices_activos.size >= 2:
            tramo_habla = activos[indices_activos[0] : indices_activos[-1] + 1]
            ratio_pausas = float(1.0 - np.mean(tramo_habla))
            duracion_locucion_s = len(tramo_habla) * (hop_len / float(sr))
        else:
            ratio_pausas = 0.4
            duracion_locucion_s = len(audio_norm) / float(sr)

        if texto_opcional and len(texto_opcional.split()) >= 2 and duracion_locucion_s > 0.25:
            rapidez_wpm = float(np.clip((len(texto_opcional.split()) / duracion_locucion_s) * 60.0, 60.0, 260.0))
        else:
            umbral_silaba = float(np.mean(rms_arr)) * 1.15
            cruces = np.sum((rms_arr[:-1] < umbral_silaba) & (rms_arr[1:] >= umbral_silaba))
            silabas_por_seg = cruces / max(0.3, duracion_locucion_s)
            rapidez_wpm = float(np.clip((silabas_por_seg / 2.1) * 60.0, 70.0, 250.0))

        # ZCR y Espectro promedio
        zcr_media = float(np.mean(zcr_lista)) if zcr_lista else 0.05
        centroide_media = float(np.mean(centroides)) if centroides else 1800.0
        rolloff_media = float(np.mean(rolloffs)) if rolloffs else 3200.0

        # MFCCs promedio y deltas (variación temporal)
        mfcc_mat = np.array(mfcc_frames, dtype=np.float32)  # Forma (n_frames, n_mfcc)
        if len(mfcc_mat) > 1:
            mfcc_medias = np.mean(mfcc_mat, axis=0)
            deltas = np.diff(mfcc_mat, axis=0)
            deltas_medias = np.mean(np.abs(deltas), axis=0)[:9]
        else:
            mfcc_medias = mfcc_mat[0] if len(mfcc_mat) else np.zeros(self.n_mfcc, dtype=np.float32)
            deltas_medias = np.zeros(9, dtype=np.float32)

        vector_features = [
            f0_media,
            f0_mediana,
            f0_std,
            f0_min,
            f0_max,
            volumen_db,
            ataque_energia,
            ratio_pausas,
            rapidez_wpm,
            zcr_media,
            centroide_media,
            rolloff_media,
            *mfcc_medias[:13],
            *deltas_medias[:9],
        ]

        # Asegurar tipo y longitud esperada (34)
        return np.array(vector_features, dtype=np.float32)

    def extraer_desde_wav(self, ruta_wav: str, texto_opcional: str = "") -> np.ndarray:
        """Carga un archivo .wav mono/stereo y extrae su vector de features."""
        with wave.open(ruta_wav, "rb") as wf:
            canales = wf.getnchannels()
            sample_width = wf.getsampwidth()
            sr = wf.getframerate()
            n_frames = wf.getnframes()
            raw_bytes = wf.readframes(n_frames)

        if sample_width == 2:
            arr = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        elif sample_width == 1:
            arr = (np.frombuffer(raw_bytes, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
        elif sample_width == 4:
            arr = np.frombuffer(raw_bytes, dtype=np.int32).astype(np.float32) / 2147483648.0
        else:
            raise ValueError(f"Ancho de muestra no soportado: {sample_width} bytes")

        if canales > 1:
            arr = arr.reshape(-1, canales).mean(axis=1)

        # Si el sample rate no es 16kHz, resamplear linealmente
        if sr != self.sample_rate:
            nuevo_largo = int(len(arr) * (self.sample_rate / float(sr)))
            arr = signal.resample(arr, nuevo_largo)

        return self.extraer_desde_audio(arr, sample_rate=self.sample_rate, texto_opcional=texto_opcional)

    def extraer_desde_pcm_bytes(
        self, muestras: bytes, sample_rate: int = 16000, sample_width: int = 2, texto_opcional: str = ""
    ) -> np.ndarray:
        """Extrae features directamente desde buffer PCM crudo del micrófono."""
        if sample_width == 2:
            arr = np.frombuffer(muestras, dtype=np.int16).astype(np.float32) / 32768.0
        else:
            arr = (np.frombuffer(muestras, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0

        if sample_rate != self.sample_rate:
            nuevo_largo = int(len(arr) * (self.sample_rate / float(sample_rate)))
            arr = signal.resample(arr, nuevo_largo)

        return self.extraer_desde_audio(arr, sample_rate=self.sample_rate, texto_opcional=texto_opcional)
