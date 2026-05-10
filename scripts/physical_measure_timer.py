import pandas as pd
import numpy as np
import time
import multiprocessing
import os
import sys

# 设置工作目录
sys.path.append(os.path.join(os.getcwd(), 'scripts'))
from real_cei_executor import _execute_wrapper

def measure_physical():
    csv_path = 'scripts/real_fuzzing_data.csv'
    df = pd.read_csv(csv_path).head(200)
    
    # 记录物理实测时间的列表
    physical_times = []
    
    print(f"开始物理动力学测速 (Gcov 插桩环境)... 计划 200 例")
    
    # 强制 spawn 模式以保持和实验一致
    multiprocessing.set_start_method('spawn', force=True)

    for i, row in df.iterrows():
        start_wall = time.perf_counter()
        
        # 模拟真实执行环境中的多进程调用
        p = multiprocessing.Process(target=_execute_wrapper, 
                                     args=(str(row['case_uid']), str(row['input_shape']), str(row['operators'])))
        p.start()
        p.join(timeout=15)
        
        if p.is_alive():
            p.terminate()
            p.join()
            
        end_wall = time.perf_counter()
        duration_ms = (end_wall - start_wall) * 1000
        physical_times.append(duration_ms)
        
        if (i+1) % 10 == 0:
            print(f"已完成 {i+1}/200 例测速...")

    # 保存物理实测结果
    df['physical_duration_ms'] = physical_times
    df.to_csv('physical_measured_perf.csv', index=False)
    print("计秒结束！物理耗时数据已保存至 physical_measured_perf.csv")

if __name__ == "__main__":
    measure_physical()
