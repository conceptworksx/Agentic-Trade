from graph.builder import app

result = app.invoke({
        "ticker_of_company":"RELIANCE.NS",
        "debate_round":0,
        "messages":[]
})

print(result["market_analyst_report"])
print(result["fundamental_analyst_report"])
print(result["technical_analyst_report"])
print(result["news_analyst_report"])
print(result["final_report"])