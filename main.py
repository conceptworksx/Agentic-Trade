from graph.builder import app

result = app.invoke({
    "messages": [ "Perform the Market Analysis"]
})

print(result["market_analyst_report"])