# Extract HSKK-relevant acoustic features
# Simplified: Only features needed for HSKK pronunciation and fluency scoring

form Extract Features
    sentence Audio_file
    sentence Output_file  
endform

# Read the sound file
Read from file: audio_file$
duration = Get total duration
name$ = selected$("Sound")

# ========== PITCH ANALYSIS (for tonal assessment) ==========
To Pitch: 0, 75, 600
pitch_mean = Get mean: 0, 0, "Hertz"
pitch_std = Get standard deviation: 0, 0, "Hertz"
pitch_min = Get minimum: 0, 0, "Hertz", "Parabolic"
pitch_max = Get maximum: 0, 0, "Hertz", "Parabolic"

select Sound 'name$'

# ========== VOICE QUALITY (HNR) ==========
To Harmonicity (cc): 0.01, 75, 0.1, 1.0
hnr_mean = Get mean: 0, 0

# ========== JITTER (pronunciation stability) ==========
select Sound 'name$'
To PointProcess (periodic, cc): 75, 600
jitter_local = Get jitter (local): 0, 0, 0.0001, 0.02, 1.3

# ========== SHIMMER (volume stability) ==========
select Sound 'name$'
plus PointProcess 'name$'
shimmer_local = Get shimmer (local): 0, 0, 0.0001, 0.02, 1.3, 1.6

# ========== SPEECH TIMING ANALYSIS (fluency) ==========
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
writeFileLine: output_file$, "# HSKK Acoustic Features"
appendFileLine: output_file$, "duration,", fixed$(duration, 3)

# Pitch (for pronunciation/tones)
appendFileLine: output_file$, "pitch_mean,", fixed$(pitch_mean, 2)
appendFileLine: output_file$, "pitch_std,", fixed$(pitch_std, 2)
appendFileLine: output_file$, "pitch_range,", fixed$(pitch_max - pitch_min, 2)

# Voice quality
appendFileLine: output_file$, "hnr_mean,", fixed$(hnr_mean, 2)

# Pronunciation stability
appendFileLine: output_file$, "jitter_local,", fixed$(jitter_local, 5)
appendFileLine: output_file$, "shimmer_local,", fixed$(shimmer_local, 5)

# Fluency metrics
appendFileLine: output_file$, "speech_rate,", fixed$(speech_rate, 2)
appendFileLine: output_file$, "articulation_rate,", fixed$(articulation_rate, 2)
appendFileLine: output_file$, "speech_duration,", fixed$(speech_duration, 3)
appendFileLine: output_file$, "pause_duration,", fixed$(pause_duration, 3)
appendFileLine: output_file$, "pause_ratio,", fixed$(pause_ratio, 3)
appendFileLine: output_file$, "num_pauses,", fixed$(num_pauses, 0)
appendFileLine: output_file$, "mean_pause_duration,", fixed$(mean_pause_duration, 3)

writeInfoLine: "HSKK features extracted to ", output_file$