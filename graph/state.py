from typing import TypedDict, Annotated, List, Literal
from langgraph.graph import MessagesState, add_messages

class InvestmentDebateState(TypedDict):

    bull_thesis: Annotated[str, "Optimistic investment thesis highlighting potential upside drivers and catalysts."]
    bear_thesis: Annotated[str, "Pessimistic investment thesis outlining key risks, weaknesses, and downside triggers."]
    debate_history: Annotated[str, "Chronological record of the investment debate discussion."]
    final_decision: Annotated[str, "Final decision made by the research manager after evaluating both perspectives."]
    debate_rounds: Annotated[int, "Number of debate iterations conducted."]

class AgentState(TypedDict):

    # --- Contextual Metadata ---
    ticker_of_company: Annotated[str, "The specific company ticker or name target for research."]
    sector_of_company: Annotated[str, "The industry vertical the company operates within (e.g., Tech, Energy)."]
    date_of_planning: Annotated[str, "The ISO-formatted date when the trading strategy planning commenced."]

    # --- Analyst Insights ---
    market_analyst_report: Annotated[str, "Comprehensive analysis of broader market regimes (Bullish/Bearish/Neutral)."]
    fundamental_analyst_report: Annotated[str, "Evaluation of financial health, including P/E ratios, debt levels, and earnings."]
    sector_analyst_report: Annotated[str, "Specific analysis of sector-level trends, tailwinds, and headwinds."]
    technical_analyst_report: Annotated[str, "Technical strength of the stock based on the indicator parameters"]
    news_analyst_report: Annotated[str, "Summary of recent high-impact news and PR events."]

    # --- Strategic Perspectives ---
    investment_debate: Annotated[
        InvestmentDebateState, 
        "Structured state capturing the ongoing investment debate, including bull and bear arguments ," \
        "discussion history, final decision, and debate iteration count."]
    investment_strategy: Annotated[str, "Final synthesized investment strategy derived from the debate."]

    # --- Orchestration & Logic ---
    debate_round: Annotated[int, "A counter tracking the number of iterations between Bull and Bear nodes."]
    research_verdict: Annotated[str, "The synthesized conclusion produced by the Research Manager."]
    trade_signal: Annotated[Literal["BUY", "SELL", "HOLD"], "The final binary or ternary trading decision."]
    risk_profile: Annotated[Literal["aggressive", "conservative"], "The risk tolerance level applied to the trade execution."]

    # --- Final Output ---
    portfolio_action: Annotated[str, "The final structured instruction for portfolio allocation or execution."]

    # --- Conversation History ---
    # We use add_messages to ensure new messages are appended to the history rather than overwriting it
    messages: Annotated[list, add_messages]

    # ----Temporary State----------
    final_report: Annotated[str , "Contains all the report and used by the aggregator"]