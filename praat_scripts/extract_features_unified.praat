# Extract HSKK-relevant acoustic features WITH per-interval analysis
# Simplified: Only features needed for HSKK scoring
# Output: JSON format

form Extract Features Unified
    sentence Audio_file
    sentence Output_file  
endform

# Read the sound file
Read from file: audio_file$
duration = Get total duration
name$ = selected$("Sound")

# ========== CREATE OBJECTS ==========
# Pitch object (for tonal assessment)
select Sound 'name$'
To Pitch: 0, 75, 600
pitch_obj$ = selected$("Pitch")

pitch_mean = Get mean: 0, 0, "Hertz"
pitch_std = Get standard deviation: 0, 0, "Hertz"
pitch_min = Get minimum: 0, 0, "Hertz", "Parabolic"
pitch_max = Get maximum: 0, 0, "Hertz", "Parabolic"

# HNR object (voice quality/clarity)
select Sound 'name$'
To Harmonicity (cc): 0.01, 75, 0.1, 1.0
hnr_obj$ = selected$("Harmonicity")
hnr_mean = Get mean: 0, 0

# PointProcess for jitter/shimmer
select Sound 'name$'
To PointProcess (periodic, cc): 75, 600
pp_obj$ = selected$("PointProcess")

# Jitter (pronunciation stability)
jitter_local = Get jitter (local): 0, 0, 0.0001, 0.02, 1.3

# Shimmer (volume stability)
select Sound 'name$'
plus PointProcess 'name$'
shimmer_local = Get shimmer (local): 0, 0, 0.0001, 0.02, 1.3, 1.6

# ========== SPEECH TIMING (TextGrid) ==========
select Sound 'name$'
To TextGrid (silences): 100, 0, -25, 0.1, 0.1, "silent", "sounding"
tg_obj$ = selected$("TextGrid")

intervals = Get number of intervals: 1
speech_duration = 0
num_pauses = 0
pause_duration = 0
num_sounding = 0

# Calculate timing stats
for i from 1 to intervals
    label$ = Get label of interval: 1, i
    start = Get start time of interval: 1, i
    end = Get end time of interval: 1, i
    interval_dur = end - start
    
    if label$ = "sounding"
        speech_duration += interval_dur
        num_sounding += 1
    elsif label$ = "silent" and interval_dur > 0.1
        num_pauses += 1
        pause_duration += interval_dur
    endif
endfor

# Calculate rates
if num_pauses > 0
    mean_pause = pause_duration / num_pauses
else
    mean_pause = 0
endif

pause_ratio = (duration - speech_duration) / duration
if pause_ratio < 0
    pause_ratio = 0
endif

if speech_duration > 0
    speech_rate = (speech_duration * 7) / duration * 60
else
    speech_rate = 0
endif

# ========== WRITE JSON OUTPUT ==========
writeFileLine: output_file$, "{"

# Overall features
appendFileLine: output_file$, "  ""overall"": {"
appendFileLine: output_file$, "    ""duration"": ", fixed$(duration, 3), ","
appendFileLine: output_file$, "    ""pitch_mean"": ", fixed$(pitch_mean, 2), ","
appendFileLine: output_file$, "    ""pitch_std"": ", fixed$(pitch_std, 2), ","
appendFileLine: output_file$, "    ""pitch_range"": ", fixed$(pitch_max - pitch_min, 2), ","
appendFileLine: output_file$, "    ""hnr_mean"": ", fixed$(hnr_mean, 2), ","
appendFileLine: output_file$, "    ""jitter_local"": ", fixed$(jitter_local, 5), ","
appendFileLine: output_file$, "    ""shimmer_local"": ", fixed$(shimmer_local, 5), ","
appendFileLine: output_file$, "    ""speech_rate"": ", fixed$(speech_rate, 2), ","
appendFileLine: output_file$, "    ""pause_ratio"": ", fixed$(pause_ratio, 3), ","
appendFileLine: output_file$, "    ""num_pauses"": ", fixed$(num_pauses, 0), ","
appendFileLine: output_file$, "    ""speech_duration"": ", fixed$(speech_duration, 3), ","
appendFileLine: output_file$, "    ""num_intervals"": ", fixed$(num_sounding, 0)
appendFileLine: output_file$, "  },"

# ========== PER-INTERVAL FEATURES ==========
appendFileLine: output_file$, "  ""intervals"": ["

select TextGrid 'tg_obj$'
interval_count = 0

for i from 1 to intervals
    select TextGrid 'tg_obj$'
    label$ = Get label of interval: 1, i
    
    if label$ = "sounding"
        start = Get start time of interval: 1, i
        end = Get end time of interval: 1, i
        interval_dur = end - start
        
        # Get pitch for this interval
        select Pitch 'pitch_obj$'
        int_pitch_mean = Get mean: start, end, "Hertz"
        int_pitch_std = Get standard deviation: start, end, "Hertz"
        
        # Get HNR for this interval
        select Harmonicity 'hnr_obj$'
        int_hnr = Get mean: start, end
        
        # Handle undefined
        if int_pitch_mean = undefined
            int_pitch_mean = 0
        endif
        if int_pitch_std = undefined
            int_pitch_std = 0
        endif
        if int_hnr = undefined
            int_hnr = 0
        endif
        
        # Write interval
        interval_count += 1
        if interval_count > 1
            appendFileLine: output_file$, "    },"
        endif
        
        appendFileLine: output_file$, "    {"
        appendFileLine: output_file$, "      ""index"": ", fixed$(interval_count, 0), ","
        appendFileLine: output_file$, "      ""start"": ", fixed$(start, 4), ","
        appendFileLine: output_file$, "      ""end"": ", fixed$(end, 4), ","
        appendFileLine: output_file$, "      ""duration"": ", fixed$(interval_dur, 4), ","
        appendFileLine: output_file$, "      ""pitch_mean"": ", fixed$(int_pitch_mean, 2), ","
        appendFileLine: output_file$, "      ""pitch_std"": ", fixed$(int_pitch_std, 2), ","
        appendFileLine: output_file$, "      ""hnr"": ", fixed$(int_hnr, 2)
    endif
endfor

# Close last interval
if interval_count > 0
    appendFileLine: output_file$, "    }"
endif

appendFileLine: output_file$, "  ]"
appendFileLine: output_file$, "}"

writeInfoLine: "HSKK features extracted to ", output_file$
