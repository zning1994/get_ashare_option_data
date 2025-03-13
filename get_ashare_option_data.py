import os
import sys
import argparse
import json
import time
from datetime import datetime
import requests
import akshare as ak
import pandas as pd

def get_option_code_list():
    # 读取 JSON 数据并处理网络错误
    url = "https://optioncodes.inology.tech/options.json"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # 确保状态码为 200
        data = response.json()

        # 转换为 pandas DataFrame
        df = pd.DataFrame(data)

        return df['期权代码'].tolist()

    except requests.exceptions.RequestException as e:
        print(f"网络请求错误: {e}")
    except ValueError as ve:
        print(f"JSON 解码错误: {ve}")
    except Exception as ex:
        print(f"发生错误: {ex}")

def option_data_fetching(target_date):
    option_code_list = get_option_code_list()
    merged_data_list = []  # 存储所有合并后的结果
    missing_data_list = []
    count = len(option_code_list)
    sum = 1

    for option_code in option_code_list:
        try:
            filtered_daily_df = pd.DataFrame()
            transposed_greeks_df = pd.DataFrame()

            # 获取每日数据
            try:
                option_sse_daily_sina_df = ak.option_sse_daily_sina(symbol=option_code)
                if not option_sse_daily_sina_df.empty:
                    option_sse_daily_sina_df['日期'] = option_sse_daily_sina_df['日期'].astype(str).str.strip()
                    filtered_daily_df = option_sse_daily_sina_df[option_sse_daily_sina_df['日期'] == target_date]
                else:
                    print(f"No daily data for {option_code}")
            except Exception as e:
                print(f"Error fetching daily data for {option_code}: {e}")

            time.sleep(0.5)

            # 获取希腊字母数据
            try:
                option_sse_greeks_sina_df = ak.option_sse_greeks_sina(symbol=option_code)
                if not option_sse_greeks_sina_df.empty:
                    transposed_greeks_df = option_sse_greeks_sina_df.set_index(option_sse_greeks_sina_df.columns[0]).T
                else:
                    print(f"No Greeks data for {option_code}")
            except Exception as e:
                print(f"Error fetching Greeks data for {option_code}: {e}")

            time.sleep(0.5)

            # 合并数据
            if not filtered_daily_df.empty and not transposed_greeks_df.empty:
                merged_df = pd.concat([filtered_daily_df.reset_index(drop=True), transposed_greeks_df.reset_index(drop=True)], axis=1)
                merged_data_list.append(merged_df)
                print(f"({sum}/{count}){merged_df.at[0, '交易代码']}({option_code}) 已完成数据整合")
                # print(merged_df)
            else:
                missing_data_list.append(option_code)
                print(f"({sum}/{count})Skipping merge for {option_code} due to missing data.")
            sum += 1

        except Exception as e:
            print(f"❌ Error processing data for {option_code}: {e}")
    print(f"There are some data missing: {str(missing_data_list)}")
    # 合并所有的 DataFrame 为一个最终的 DataFrame
    if merged_data_list:
        final_merged_df = pd.concat(merged_data_list, ignore_index=True)
        print("\n✅ Final Merged DataFrame Completed")
        # print(final_merged_df)
        return final_merged_df
    else:
        print("No data merged.")
        return pd.DataFrame()

def option_data_fetching_em(target_date):
    option_current_em_df = ak.option_current_em()
    option_value_analysis_em_df = ak.option_value_analysis_em()
    option_risk_analysis_em_df = ak.option_risk_analysis_em()

    option_value_analysis_em_df.drop(columns=['最新价'], inplace=True)
    option_risk_analysis_em_df.drop(columns=['最新价','涨跌幅'], inplace=True)

    result = pd.merge(option_value_analysis_em_df, option_risk_analysis_em_df, on=['期权代码','期权名称','到期日'], how='left')
    result = pd.merge(option_current_em_df, result, left_on="代码", right_on='期权代码', how='inner')

    result.drop(columns=['序号','期权代码','期权名称'], inplace=True)
    print(result)
    return result
    # result.to_csv("option_risk_analysis_em.csv", index=False)

if __name__ == '__main__':
    # 添加命令行参数解析
    parser = argparse.ArgumentParser(description="Fetch option data")
    parser.add_argument('--mode', choices=['em', 'all'], default='all', help="Select mode: 'em' for only em data, 'all' for all data")
    args = parser.parse_args()

    target_date = '2025-02-21'
    # 获取历史交易日数据
    tool_trade_date_hist_sina_df = ak.tool_trade_date_hist_sina()

    # 将 trade_date 列转换为字符串类型
    tool_trade_date_hist_sina_df['trade_date'] = tool_trade_date_hist_sina_df['trade_date'].astype(str)

    # 获取今天的日期
    today = datetime.today().strftime("%Y-%m-%d")

    # 判断今天是否是交易日
    if today in tool_trade_date_hist_sina_df['trade_date'].values:
        print(f"今天 {today} 是交易日 ✅")
        target_date = today
    else:
        print(f"今天 {today} 不是交易日 ❌，程序即将退出。")
        sys.exit(0)  # 正常退出程序

    # 根据模式执行相应的部分
    if args.mode in ['em', 'all']:
        result_em = option_data_fetching_em(target_date)
        if not result_em.empty:
            # 创建目标目录 data/{target_date}
            output_dir = os.path.join("data", target_date)
            os.makedirs(output_dir, exist_ok=True)

            # 设置输出文件路径
            output_file = os.path.join(output_dir, "option_data_em.csv")

            # 保存 CSV 文件
            result_em.to_csv(output_file, index=False)
            print(f"✅ Data saved to {output_file}")
        else:
            print("⚠️ No data to save.")

    if args.mode in ['s', 'all']:
        result = option_data_fetching(target_date)
        if not result.empty:
            # 创建目标目录 data/{target_date}
            output_dir = os.path.join("data", target_date)
            os.makedirs(output_dir, exist_ok=True)

            # 设置输出文件路径
            output_file = os.path.join(output_dir, "option_data.csv")

            # 保存 CSV 文件
            result.to_csv(output_file, index=False)
            print(f"✅ Data saved to {output_file}")
        else:
            print("⚠️ No data to save.")
