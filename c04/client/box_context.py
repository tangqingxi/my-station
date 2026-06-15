# client/box_context.py · 客户端装配坐标 · 只描述要连接哪台服务器、哪台箱


class ClientBoxContext:
    def __init__(self, device_id, host, port):
        self.device_id = int(device_id)
        self.host = host
        self.port = int(port)
