import sys
import json
import time
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

def option_data_fetching():
    option_code_list = get_option_code_list()
    merged_data_list = []  # 存储所有合并后的结果
    missing_data_list = []
    target_date = "2025-02-21"
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

if __name__ == '__main__':
    result = option_data_fetching()
    if not result.empty:
        result.to_csv('option_data.csv', index=False)
        print("✅ Data saved to option_data.csv")
    else:
        print("⚠️ No data to save.")
