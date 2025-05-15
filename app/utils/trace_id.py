from fastapi import Request


# Trích xuất trace_id từ request (nếu đã được middleware gán vào headers hoặc state)
def get_request_trace_id(request: Request) -> str:
    # Ưu tiên từ header
    trace_id = request.headers.get("X-Trace-Id")
    if not trace_id:
        # Hoặc từ request.state (nếu bạn dùng middleware để gán)
        trace_id = getattr(request.state, "trace_id", None)
    return trace_id or "unknown"
