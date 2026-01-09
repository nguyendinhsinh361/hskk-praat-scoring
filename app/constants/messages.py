"""
Vietnamese Feedback Messages - All user-facing text constants
"""

# ========== Error Messages ==========
ERROR_SCORING = "Không thể chấm điểm tiêu chí này"
ERROR_NO_AUDIO_DATA = "Không có dữ liệu âm thanh"
ERROR_NO_SCORING_RESULT = "Không có kết quả chấm điểm"
ERROR_SCORING_TEMPLATE = "Scoring error: {error}"
ERROR_UNIFIED_SCORING_TEMPLATE = "Unified scoring error: {error}"
ERROR_GPT_FEEDBACK = "Không thể tạo nhận xét chi tiết"
ERROR_RETRY_LATER = "Vui lòng thử lại sau"

# ========== Pronunciation Feedback ==========
FEEDBACK_PRONUNCIATION_EXCELLENT = "Phát âm rõ ràng, không có lỗi sai. Giọng đọc tự nhiên, gần với chuẩn phổ thông."
FEEDBACK_PRONUNCIATION_GOOD = "Phát âm tương đối tốt, có một vài điểm cần cải thiện nhỏ."
FEEDBACK_PRONUNCIATION_ACCEPTABLE_PREFIX = "Phát âm cơ bản đạt yêu cầu nhưng cần cải thiện: "
FEEDBACK_PRONUNCIATION_ACCEPTABLE_DEFAULT = "độ ổn định của giọng"
FEEDBACK_PRONUNCIATION_POOR_PREFIX = "Mức độ kiểm soát cơ quan phát âm chưa tốt. "
FEEDBACK_PRONUNCIATION_POOR_SUFFIX = "Các vấn đề cần khắc phục: "

# Pronunciation Issues (Vietnamese)
ISSUE_LOW_HNR = "Độ trong của giọng chưa tốt (HNR thấp)"
ISSUE_NOISY_VOICE = "Giọng nói có nhiều nhiễu, thiếu độ trong"
ISSUE_HIGH_JITTER = "Tần số giọng không ổn định (jitter cao)"
ISSUE_UNSTABLE_VOICE_SEVERE = "Giọng nói thiếu ổn định nghiêm trọng"
ISSUE_HIGH_SHIMMER = "Âm lượng không đều (shimmer cao)"
ISSUE_HIGH_SHIMMER_SEVERE = "Âm lượng biến thiên quá lớn"
ISSUE_PITCH_DEVIATION_TEMPLATE = "Cao độ lệch ({pitch:.0f}Hz)"
ISSUE_UNSTABLE_TONE = "Thanh điệu không ổn định"
ISSUE_UNCLEAR_VOICE_TEMPLATE = "Giọng chưa rõ (HNR={hnr:.1f})"
ISSUE_LOW_CLARITY = "Độ trong giọng thấp"

# ========== Fluency Feedback ==========
FEEDBACK_FLUENCY_EXCELLENT = "Tốc độ lời nói ổn định, không có ngập ngừng đáng kể. Ngữ điệu tự nhiên."
FEEDBACK_FLUENCY_GOOD_TEMPLATE = "Độ trôi chảy tốt, có một điểm cần cải thiện: {issue}."
FEEDBACK_FLUENCY_ACCEPTABLE_PREFIX = "Mạch lời nói cơ bản đạt yêu cầu. Cần cải thiện: "
FEEDBACK_FLUENCY_POOR_PREFIX = "Mạch lời nói rời rạc, thiếu sự điều tiết về nhịp và cao độ. "
FEEDBACK_FLUENCY_POOR_SUFFIX = "Các vấn đề: "

# Fluency Issues (Vietnamese)
ISSUE_SPEECH_TOO_SLOW = "Tốc độ nói quá chậm"
ISSUE_SPEECH_SLIGHTLY_SLOW = "Tốc độ nói hơi chậm"
ISSUE_SPEECH_TOO_FAST = "Tốc độ nói quá nhanh"
ISSUE_SPEECH_SLIGHTLY_FAST = "Tốc độ nói hơi nhanh"
ISSUE_TOO_MANY_PAUSES = "Ngắt nghỉ quá nhiều"
ISSUE_PAUSES_TOO_LONG = "Thời gian ngắt nghỉ quá dài"
ISSUE_HESITATION = "Ngập ngừng nhiều lần"
ISSUE_SPEED_UNSTABLE = "Tốc độ nói không ổn định"

# Problem codes for Fluency
PROBLEM_WRONG_PAUSE = "ngat_nghi_sai"
PROBLEM_HESITATION = "ngap_ngung"
PROBLEM_SPEED_UNSTABLE = "toc_do_khong_on_dinh"

# ========== Criteria Names (Vietnamese) ==========
CRITERIA_NAME_PRONUNCIATION = "Phát âm (Pronunciation)"
CRITERIA_NAME_FLUENCY = "Độ trôi chảy (Fluency)"
CRITERIA_NAME_TASK_ACHIEVEMENT = "Hoàn thành nhiệm vụ"
CRITERIA_NAME_GRAMMAR = "Ngữ pháp"
CRITERIA_NAME_VOCABULARY = "Từ vựng"
CRITERIA_NAME_COHERENCE = "Tính mạch lạc"

# ========== Chinese Punctuation ==========
CHINESE_PUNCTUATION = "。，！？、"
