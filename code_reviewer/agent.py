from code_reviewer.agents import ReviewAgent

# Create an instance of ReviewAgent and expose its agent as root_agent
review_agent = ReviewAgent()
root_agent = review_agent.agent
