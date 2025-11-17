# Responsible AI in Practice
## Building agents with context aware security
### Overview

This notebook demonstrates how to utilize Bedrock AgentCore to implement programmatic controls that protect controlled/sensitive information by dynamically managing tool access. We will build an AI Agent that:
1. Uses tool semantic search to discover the most relevant actions given a query.
2. Applies context-aware security strategies to determine whether the agent can access tools capable of leaking sensitive/controlled data.
3. Stores conversational memory tagged with classification (`public` or `controlled`) for fine-grained retrieval control.

By the end of this tutorial, you'll be able to:
- Invoke an agent that only uses tools appropriate for the current context.
- Manage memory retrieval based on tool classifications.
- Deploy an agent with Responsible AI practices to safeguard sensitive data.

This workflow is applicable across industries, and we have structured the notebook to allow for users to easily modify it for their use-cases.
**Prerequisites**:
> - An AWS account with Amazon Bedrock models as well as Bedrock AgentCore access enabled.
> - A Cognito User Pool to obtain OAuth tokens (`APPLICATION_USERPOOL_ID`, `APPLICATION_CLIENT_ID`, `APPLICATION_CLIENT_SECRET`)
> - Install required Python packages (handles below)
