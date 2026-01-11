'use client';

import { createChart, ColorType, CandlestickSeries, Time, CandlestickData } from 'lightweight-charts';
import React, { useEffect, useRef } from 'react';
import { Candle } from '@/services/api';

interface ChartComponentProps {
  data: Candle[];
}

export const ChartComponent: React.FC<ChartComponentProps> = ({ data }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const handleResize = () => {
      chart.applyOptions({ width: chartContainerRef.current!.clientWidth });
    };

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#18181b' }, // Zinc-900
        textColor: '#d4d4d8',
      },
      grid: {
        vertLines: { color: '#27272a' },
        horzLines: { color: '#27272a' },
      },
      width: chartContainerRef.current.clientWidth,
      height: 400,
    });

    // v5 API: Use addSeries with CandlestickSeries
    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#10b981', // Emerald-500
      downColor: '#ef4444', // Red-500
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });

    candlestickSeries.setData(data as unknown as CandlestickData<Time>[]);

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data]);

  return (
    <div ref={chartContainerRef} className="w-full h-[400px] rounded-lg overflow-hidden border border-zinc-800" />
  );
};
