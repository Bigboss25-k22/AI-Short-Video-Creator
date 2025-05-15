# app/common/schema.py

# Mapping mã lỗi pydantic => thông báo lỗi tùy chỉnh
CUSTOM_VALIDATION_ERROR_MESSAGES = {
    "value_error.missing": "Trường này là bắt buộc",
    "value_error.any_str.min_length": "Độ dài tối thiểu là {limit_value} ký tự",
    "value_error.any_str.max_length": "Độ dài tối đa là {limit_value} ký tự",
    "type_error.integer": "Phải là số nguyên",
    "type_error.string": "Phải là chuỗi",
    "value_error.number.not_ge": "Phải lớn hơn hoặc bằng {limit_value}",
    "value_error.number.not_le": "Phải nhỏ hơn hoặc bằng {limit_value}",
    "type_error.list": "Phải là danh sách",
    "type_error.dict": "Phải là dictionary",
    "value_error.email": "Email không hợp lệ",
    "json_invalid": "JSON không hợp lệ",  # Có thể dùng để check payload
}
