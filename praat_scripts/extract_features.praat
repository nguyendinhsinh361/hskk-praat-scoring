# Extract comprehensive acoustic features for HSKK scoring
    form Extract Features
        sentence Audio_file
        sentence Output_file  
    endform
    
    # Read the sound file
    Read from file: audio_file$
    duration = Get total duration
    name$ = selected$("Sound")
    
    # ========== PITCH ANALYSIS ==========
    To Pitch: 0, 75, 600
    pitch_mean = Get mean: 0, 0, "Hertz"
    pitch_std = Get standard deviation: 0, 0, "Hertz"
    pitch_min = Get minimum: 0, 0, "Hertz", "Parabolic"
    pitch_max = Get maximum: 0, 0, "Hertz", "Parabolic"
    pitch_median = Get quantile: 0, 0, 0.50, "Hertz"
    pitch_q25 = Get quantile: 0, 0, 0.25, "Hertz"
    pitch_q75 = Get quantile: 0, 0, 0.75, "Hertz"
    
    select Sound 'name$'
    
    # ========== FORMANT ANALYSIS (F1-F4) ==========
    To Formant (burg): 0, 5, 5500, 0.025, 50
    f1_mean = Get mean: 1, 0, 0, "Hertz"
    f1_std = Get standard deviation: 1, 0, 0, "Hertz"
    f2_mean = Get mean: 2, 0, 0, "Hertz"
    f2_std = Get standard deviation: 2, 0, 0, "Hertz"
    f3_mean = Get mean: 3, 0, 0, "Hertz"
    f3_std = Get standard deviation: 3, 0, 0, "Hertz"
    f4_mean = Get mean: 4, 0, 0, "Hertz"
    f4_std = Get standard deviation: 4, 0, 0, "Hertz"
    
    select Sound 'name$'
    
    # ========== INTENSITY ANALYSIS ==========
    To Intensity: 100, 0, "yes"
    intensity_mean = Get mean: 0, 0, "energy"
    intensity_std = Get standard deviation: 0, 0
    intensity_min = Get minimum: 0, 0, "Parabolic"
    intensity_max = Get maximum: 0, 0, "Parabolic"
    
    select Sound 'name$'
    
    # ========== SPECTRAL ANALYSIS ==========
    To Spectrum: "yes"
    spectral_centroid = Get centre of gravity: 2
    spectral_std = Get standard deviation: 2
    spectral_skewness = Get skewness: 2
    spectral_kurtosis = Get kurtosis: 2
    
    # Band energy for COG and spread
    band_energy_low = Get band energy: 0, 500
    band_energy_mid = Get band energy: 500, 2000
    band_energy_high = Get band energy: 2000, 4000
    total_energy = band_energy_low + band_energy_mid + band_energy_high
    
    if total_energy > 0
        cog = (band_energy_low * 250 + band_energy_mid * 1250 + band_energy_high * 3000) / total_energy
        spread = band_energy_high - band_energy_low
    else
        cog = 1000
        spread = 0
    endif
    
    # Calculate spectral slope using band energies
    if band_energy_low > 0 and band_energy_high > 0
        slope = (band_energy_high - band_energy_low) / (band_energy_high + band_energy_low)
    else
        slope = 0
    endif
    
    select Sound 'name$'
    
    # ========== VOICE QUALITY (HNR) ==========
    To Harmonicity (cc): 0.01, 75, 0.1, 1.0
    hnr_mean = Get mean: 0, 0
    hnr_std = Get standard deviation: 0, 0
    
    # ========== JITTER ANALYSIS ==========
    select Sound 'name$'
    To PointProcess (periodic, cc): 75, 600
    jitter_local = Get jitter (local): 0, 0, 0.0001, 0.02, 1.3
    jitter_rap = Get jitter (rap): 0, 0, 0.0001, 0.02, 1.3
    jitter_ppq5 = Get jitter (ppq5): 0, 0, 0.0001, 0.02, 1.3
    
    # ========== SHIMMER ANALYSIS ==========
    select Sound 'name$'
    plus PointProcess 'name$'
    shimmer_local = Get shimmer (local): 0, 0, 0.0001, 0.02, 1.3, 1.6
    shimmer_apq3 = Get shimmer (apq3): 0, 0, 0.0001, 0.02, 1.3, 1.6
    shimmer_apq5 = Get shimmer (apq5): 0, 0, 0.0001, 0.02, 1.3, 1.6
    shimmer_apq11 = Get shimmer (apq11): 0, 0, 0.0001, 0.02, 1.3, 1.6
    
    # ========== SPEECH TIMING ANALYSIS ==========
    select Sound 'name$'
    To TextGrid (silences): 100, 0, -25, 0.1, 0.1, "silent", "sounding"
    intervals = Get number of intervals: 1
    speech_duration = 0
    num_pauses = 0
    total_pause_duration = 0
    
    for i from 1 to intervals
        label$ = Get label of interval: 1, i
        start = Get start time of interval: 1, i
        end = Get end time of interval: 1, i
        interval_duration = end - start
        
        if label$ = "sounding"
            speech_duration += interval_duration
        elsif label$ = "silent" and interval_duration > 0.1
            num_pauses += 1
            total_pause_duration += interval_duration
        endif
    endfor
    
    pause_duration = total_pause_duration
    if num_pauses > 0
        mean_pause_duration = total_pause_duration / num_pauses
    else
        mean_pause_duration = 0
    endif
    
    # Calculate speech rates
    if speech_duration > 0
        estimated_syllables = speech_duration * 7
        speech_rate = estimated_syllables / duration * 60
        articulation_rate = estimated_syllables / speech_duration * 60
    else
        speech_rate = 0
        articulation_rate = 0
    endif
    
    pause_ratio = (duration - speech_duration) / duration
    
    # ========== WRITE RESULTS ==========
    writeFileLine: output_file$, "# HSKK Comprehensive Acoustic Features"
    appendFileLine: output_file$, "duration,", fixed$(duration, 3)
    
    appendFileLine: output_file$, "pitch_mean,", fixed$(pitch_mean, 2)
    appendFileLine: output_file$, "pitch_std,", fixed$(pitch_std, 2)
    appendFileLine: output_file$, "pitch_range,", fixed$(pitch_max - pitch_min, 2)
    appendFileLine: output_file$, "pitch_min,", fixed$(pitch_min, 2)
    appendFileLine: output_file$, "pitch_max,", fixed$(pitch_max, 2)
    appendFileLine: output_file$, "pitch_median,", fixed$(pitch_median, 2)
    appendFileLine: output_file$, "pitch_quantile_25,", fixed$(pitch_q25, 2)
    appendFileLine: output_file$, "pitch_quantile_75,", fixed$(pitch_q75, 2)
    
    appendFileLine: output_file$, "f1_mean,", fixed$(f1_mean, 2)
    appendFileLine: output_file$, "f1_std,", fixed$(f1_std, 2)
    appendFileLine: output_file$, "f2_mean,", fixed$(f2_mean, 2)
    appendFileLine: output_file$, "f2_std,", fixed$(f2_std, 2)
    appendFileLine: output_file$, "f3_mean,", fixed$(f3_mean, 2)
    appendFileLine: output_file$, "f3_std,", fixed$(f3_std, 2)
    appendFileLine: output_file$, "f4_mean,", fixed$(f4_mean, 2)
    appendFileLine: output_file$, "f4_std,", fixed$(f4_std, 2)
    
    appendFileLine: output_file$, "intensity_mean,", fixed$(intensity_mean, 2)
    appendFileLine: output_file$, "intensity_std,", fixed$(intensity_std, 2)
    appendFileLine: output_file$, "intensity_min,", fixed$(intensity_min, 2)
    appendFileLine: output_file$, "intensity_max,", fixed$(intensity_max, 2)
    
    appendFileLine: output_file$, "spectral_centroid,", fixed$(spectral_centroid, 2)
    appendFileLine: output_file$, "spectral_std,", fixed$(spectral_std, 2)
    appendFileLine: output_file$, "spectral_skewness,", fixed$(spectral_skewness, 2)
    appendFileLine: output_file$, "spectral_kurtosis,", fixed$(spectral_kurtosis, 2)
    
    appendFileLine: output_file$, "hnr_mean,", fixed$(hnr_mean, 2)
    appendFileLine: output_file$, "hnr_std,", fixed$(hnr_std, 2)
    
    appendFileLine: output_file$, "jitter_local,", fixed$(jitter_local, 5)
    appendFileLine: output_file$, "jitter_rap,", fixed$(jitter_rap, 5)
    appendFileLine: output_file$, "jitter_ppq5,", fixed$(jitter_ppq5, 5)
    
    appendFileLine: output_file$, "shimmer_local,", fixed$(shimmer_local, 5)
    appendFileLine: output_file$, "shimmer_apq3,", fixed$(shimmer_apq3, 5)
    appendFileLine: output_file$, "shimmer_apq5,", fixed$(shimmer_apq5, 5)
    appendFileLine: output_file$, "shimmer_apq11,", fixed$(shimmer_apq11, 5)
    
    appendFileLine: output_file$, "speech_rate,", fixed$(speech_rate, 2)
    appendFileLine: output_file$, "articulation_rate,", fixed$(articulation_rate, 2)
    appendFileLine: output_file$, "speech_duration,", fixed$(speech_duration, 3)
    appendFileLine: output_file$, "pause_duration,", fixed$(pause_duration, 3)
    appendFileLine: output_file$, "pause_ratio,", fixed$(pause_ratio, 3)
    appendFileLine: output_file$, "num_pauses,", fixed$(num_pauses, 0)
    appendFileLine: output_file$, "mean_pause_duration,", fixed$(mean_pause_duration, 3)
    
    appendFileLine: output_file$, "cog,", fixed$(cog, 2)
    appendFileLine: output_file$, "slope,", fixed$(slope, 4)
    appendFileLine: output_file$, "spread,", fixed$(spread, 2)
    
    writeInfoLine: "Comprehensive features extracted to ", output_file$