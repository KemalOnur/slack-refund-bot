import time, random



class RefundService:
    def refund(self, order_id:str, amount:float, currency:str, reason:str):
        time.sleep(0.2)
        if random.random() < 0.15:
            return False, None, "mock transient error"
        ext_id = f"Mock-{int(time.time())}"
        return True, ext_id, None