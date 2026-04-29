from graph.builder import app

result = app.invoke({
        "ticker_of_company":"RELIANCE.NS",
        "investment_debate": {
        "bull_thesis": "",
        "bear_thesis": "",
        "debate_history": "",
        "final_decision": "",
        "current_response": "",
        "debate_rounds": 0  
         },
        "messages":[]
})

print(result["market_analyst_report"])
print(result["fundamental_analyst_report"])
print(result["technical_analyst_report"])
print(result["news_analyst_report"])
print(result["investment_debate"])