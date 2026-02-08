
import numpy as np

class RiskManager:
    """
    Kelly Criterion & Neural Position Sizing
    Parayı matematiksel olarak yönetir.
    """
    def __init__(self, fraction=0.5):
        # 'fraction' (Fractional Kelly) risk iştahını belirler. 
        # 0.5 = Yarı Kelly (Daha güvenli)
        self.fraction = fraction

    def calculate_position_size(self, win_probability, win_loss_ratio=1.5):
        """
        Kelly Formülü: f* = p - (1-p) / b
        p = Kazanma ihtimali (AI Confidence)
        b = Kazanç/Kayıp oranı (Reward/Risk)
        """
        p = win_probability
        q = 1.0 - p
        b = win_loss_ratio
        
        # Kelly Payı
        kelly_f = p - (q / b)
        
        # Sadece pozitif ve mantıklı oranları döndür
        # Fractional Kelly uygulayarak riski azaltıyoruz
        safe_size = max(0, kelly_f * self.fraction)
        
        # Tek işlemde kasanın max %25'inden fazlasını basma (Güvenlik Sınırı)
        return min(0.25, safe_size)

risk_engine = RiskManager(fraction=0.3) # Muhafazakar Kelly
