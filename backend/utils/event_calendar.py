
import pandas as pd
import numpy as np
from datetime import datetime

class EventCalendar:
    """
    Ekonomik ve Finansal Olaylar Takvimi (2015-2026)
    Piyasa yapıcı olayların tarihlerini ve etkilerini saklar.
    """
    def __init__(self):
        # Önemli olaylar: (Tarih, Olay Tipi, Etki Gücü 1-10)
        self.events = [
            # Halvingler
            ("2016-07-09", "HALVING", 10),
            ("2020-05-11", "HALVING", 10),
            ("2024-04-20", "HALVING", 10),
            # Krizler / Büyük Olaylar
            ("2020-03-12", "PANDEMIC_CRASH", 10),
            ("2021-04-14", "COINBASE_IPO", 7),
            ("2022-05-07", "LUNA_CRASH", 9),
            ("2022-11-08", "FTX_CRASH", 9),
            ("2024-01-10", "BTC_ETF_APPROVAL", 8),
            # FED (Önemli Faiz Karar Dönemleri - Örnekler)
            ("2022-03-16", "FED_RATE_HIKE_START", 8),
            ("2024-09-18", "FED_RATE_CUT_START", 8),
        ]
        
    def get_event_features(self, df_dates):
        """
        Verilen tarih serisi için 'Olay Yakınlığı' özelliklerini üretir.
        """
        features = pd.DataFrame(index=df_dates)
        
        # Günleri datetime'a çevir
        df_dates = pd.to_datetime(df_dates)
        
        # Her bir olay tipi için 'Gün Kaldı' veya 'Gün Geçti' özelliği
        for event_date, event_name, power in self.events:
            e_date = pd.to_datetime(event_date)
            # Olay anına olan uzaklık (gün bazında)
            diff = (df_dates - e_date).days
            # Sadece olayın 30 gün öncesi ve 30 gün sonrasını işaretle
            features[f'event_{event_name}'] = np.where((diff >= -30) & (diff <= 30), power / (abs(diff) + 1), 0)
            
        return features

event_engine = EventCalendar()
