import asyncio
import os
from signal import SIGTERM, SIGINT, signal
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

from finmcp import MCP_CONNECTIONS, start_all_services, close_all_services

import dotenv


dotenv.load_dotenv()


async def main():
    start_all_services()

    signal(SIGINT, lambda sig, frame: close_all_services())
    signal(SIGTERM, lambda sig, frame: close_all_services())

    client = MultiServerMCPClient(connections=MCP_CONNECTIONS)
    tools = await client.get_tools()
    print(tools)

    llm = ChatOpenAI(
        model="gpt-5.1",
        api_key=os.getenv("OPENAI_API_KEY", ""),
        temperature=0,
        max_retries=5,
    )
    agent = create_agent(
        model = llm, 
        tools = tools,
        system_prompt=\
            "所有的数据必须从工具中获取，不能凭空编造数据。" \
            "对于指数数据，先用list_indices工具获取有效的symbol，再用history工具获取数据。" \
            "特别注意不同数据源的symbol格式可能不同，使用时要确认清楚。" \
            "比如yahoo finance的汇率数据的symbol格式是'AUDCAD=X'，而investing.com的格式是'aud-cad'" \
            "回答时要说明数据来源于哪个数据源。",
    )
    while True:
        print(">>> ", end="")
        try:
            user_input = input()
        except EOFError:
            break
        result = await agent.ainvoke({
            "messages": [
                {
                    "role": "user",
                    "content": user_input  \
                }
            ]
        })

        if result.get("messages") is None:
            print("Failed to get response after 3 tries.")
            continue
        for m in result["messages"]:
            if m.type == "tool" or m.type == "ai":
                if m.content: print(m.type, ":", m.content)

    close_all_services()

if __name__ == "__main__":
    from finmcp.data_sources.fin_history import DATASOURCES, DataType, DataFrequency
    from datetime import datetime, date
    # tu = DATASOURCES['tushare']()
    yf = DATASOURCES['yahoo_finance']()
    # ic = DATASOURCES['investing.com']()
    # nh = DATASOURCES['nanhua']()
    # df_tu = tu.history("000001.sh", type=DataType.INDEX, start="2000-01-01", end=datetime.now(), freq=DataFrequency.DAILY)
    # df_yf = yf.history("AAAA", type=DataType.STOCK, start="2000-01-01", end=datetime.now(), freq=DataFrequency.DAILY)
    df_yf = yf.history("AAAA", type=DataType.STOCK, start="2024-01-01", end=datetime.now(), freq=DataFrequency.MINUTE60)
    # df_ic = ic.history("usd-cny", type=DataType.FOREX, start="2000-01-01", end=datetime.now(), freq=DataFrequency.DAILY)
    # df_nh = nh.history("PP_NH", type=DataType.COMMODITY, start="2000-01-01", end=datetime.now(), freq=DataFrequency.DAILY)
    # print(df_tu)
    print(df_yf)
    # print(df_ic)
    # print(df_nh)

# if __name__ == "__main__":
#     asyncio.run(main())