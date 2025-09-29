# Extract acoustic features for HSKK scoring
    form Extract Features
        sentence Audio_file
        sentence Output_file  
    endform
    
    # Read the sound file
    Read from file: audio_file$
    
    # Get basic info
    duration = Get total duration
    name$ = selected$("Sound")
    
    # Extract pitch (F0)
    To Pitch: 0, 75, 600
    pitch_mean = Get mean: 0, 0, "Hertz"
    pitch_std = Get standard deviation: 0, 0, "Hertz"
    pitch_min = Get minimum: 0, 0, "Hertz", "Parabolic"
    pitch_max = Get maximum: 0, 0, "Hertz", "Parabolic"
    
    select Sound 'name$'
    
    # Extract formants
    To Formant (burg): 0, 5, 5500, 0.025, 50
    f1_mean = Get mean: 1, 0, 0, "Hertz"
    f2_mean = Get mean: 2, 0, 0, "Hertz"  
    f3_mean = Get mean: 3, 0, 0, "Hertz"
    
    select Sound 'name$'
    
    # Extract intensity
    To Intensity: 100, 0, "yes"
    intensity_mean = Get mean: 0, 0, "energy"
    intensity_std = Get standard deviation: 0, 0
    
    select Sound 'name$'
    
    # Extract spectral features
    To Spectrum: "yes"
    spectral_centroid = Get centre of gravity: 2
    
    # Voice quality measures
    select Sound 'name$'
    To Harmonicity (cc): 0.01, 75, 0.1, 1.0
    hnr_mean = Get mean: 0, 0
    
    # Calculate speech rate (simplified)
    select Sound 'name$'
    To TextGrid (silences): 100, 0, -25, 0.1, 0.1, "silent", "sounding"
    intervals = Get number of intervals: 1
    speech_duration = 0
    
    for i from 1 to intervals
        label$ = Get label of interval: 1, i
        if label$ = "sounding"
            start = Get start time of interval: 1, i
            end = Get end time of interval: 1, i
            speech_duration += (end - start)
        endif
    endfor
    
    if speech_duration > 0
        estimated_syllables = speech_duration * 7
        speech_rate = estimated_syllables / duration * 60
    else
        speech_rate = 0
    endif
    
    # Write results
    writeFileLine: output_file$, "# HSKK Acoustic Features"
    appendFileLine: output_file$, "duration,", fixed$(duration, 3)
    appendFileLine: output_file$, "pitch_mean,", fixed$(pitch_mean, 2)
    appendFileLine: output_file$, "pitch_std,", fixed$(pitch_std, 2)
    appendFileLine: output_file$, "pitch_range,", fixed$(pitch_max - pitch_min, 2)
    appendFileLine: output_file$, "f1_mean,", fixed$(f1_mean, 2)
    appendFileLine: output_file$, "f2_mean,", fixed$(f2_mean, 2)
    appendFileLine: output_file$, "f3_mean,", fixed$(f3_mean, 2)
    appendFileLine: output_file$, "intensity_mean,", fixed$(intensity_mean, 2)
    appendFileLine: output_file$, "intensity_std,", fixed$(intensity_std, 2)
    appendFileLine: output_file$, "spectral_centroid,", fixed$(spectral_centroid, 2)
    appendFileLine: output_file$, "hnr_mean,", fixed$(hnr_mean, 2)
    appendFileLine: output_file$, "speech_rate,", fixed$(speech_rate, 2)
    appendFileLine: output_file$, "speech_duration,", fixed$(speech_duration, 3)
    appendFileLine: output_file$, "pause_ratio,", fixed$((duration - speech_duration) / duration, 3)
    
    writeInfoLine: "Features extracted to ", output_file$