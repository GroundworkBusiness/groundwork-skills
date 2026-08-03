---
name: connector-check
description: Review any AI connector before and after it is connected. Check the real job, permissions, available actions, tool and token-context effect, and whether the connection still earns its place.
---

# Connector Check

Help me review a connector carefully. Use this before I connect a tool, whenever a connected tool changes, and during periodic reviews of the tools I already have connected. The goal is a useful, accountable connection, not broad access by default.

## Rules

- Ask questions before recommending a connection or asking me to authorize anything.
- Start with the smallest useful scope. Prefer read-only access for a first test and for any connection that does not need to change data.
- For email, a CRM, personnel records, financial systems, client records, or other sensitive sources, do not recommend a connection unless I explicitly confirm that I am authorized, the task truly requires it, and I understand the provider's access scope.
- Never create, edit, send, delete, share, or move anything in a connected tool unless I explicitly approve that specific action after seeing the plan.
- Describe provider permissions and in-app action controls in plain English. If either is unclear, tell me what to confirm before I continue.
- Inspect the available tool list. A server may expose many tools, and their descriptions can consume working context even when I use only one of them.
- If the connector is unavailable, suggest a manual, temporary alternative. Do not pretend the connection exists.

## Step 1: Start with the tool and job

Ask me these questions, one at a time if helpful:

1. What tool are you considering connecting or reviewing?
2. What real task would you complete with this tool?
3. What information or action does that task actually need?
4. Is the account and information appropriate for this AI tool, and are you authorized to use it here?
5. Does the task need only read access, or does it truly need create, update, send, share, or delete access?
6. Which connectors are already active in this workspace, if any?

Summarize the answer in this format:

> **Tool:** [connector or outside tool]
> **Job:** [specific outcome]
> **What it needs:** [specific information and/or action]
> **Why a connection helps:** [what repeated step it removes]

If the job is still broad, help me narrow it before discussing a connector.

## Step 2: Run the access check

Classify the source and explain the result:

| Source type | Connection guidance |
|---|---|
| My own calendar or a non-sensitive shared calendar | Usually workable for a read-only test. Confirm exactly which calendar and actions are available. |
| A non-sensitive folder or document library | Check whether the provider permission is limited to selected files or grants broader Drive/library access. |
| Email, CRM, HR, finance, health, student, client, or other protected records | Treat as sensitive and potentially broad. Confirm authorization, policy, provider scope, and the exact task before recommending a connection. |
| A tool I do not recognize or do not control | Do not connect it until I understand the owner, permissions, and business purpose. |

If the source or requested access is not appropriate, offer one safer alternative and explain why.

## Step 3: Make a connector card

Before I click Connect, show this card and wait for my approval:

> **Connector:** [name]
> **One job:** [specific task]
> **Account and source access:** [plain-English provider scope]
> **What it needs to read or do:** [exact calendar, folder, data, or action]
> **Enabled actions:** [read / create / update / send / share / delete, with unnecessary actions disabled when the app allows it]
> **Tools and token-context check:** [available tool count; displayed token impact if available, otherwise expected LOW / MEDIUM / HIGH effect]
> **Test:** [one read-only task]
> **Stop condition:** [what would make us disconnect or choose another route]

If the provider scope, enabled actions, or tool/context effect are not justified by the job, recommend declining the connection, disabling unnecessary actions, or looking for a narrower option.

## Step 4: Connect or review and test

For a new connection, only after I approve the connector card:

1. Guide me through the connection screen without guessing what it says.
2. Check the available actions and tool list after connection. Disable any action that is not needed when the AI app allows it.
3. Run the one read-only test we agreed on.
4. Show me the result and ask me to verify that it is accurate and within scope.
5. Do not take any write action, even if the connector offers it.

For an existing connection, skip the authorization screen. Review its current provider scope, available actions, tool list, and real job before running the agreed read-only test.

## Step 5: Close the loop and summarize connections

Finish with a short record for the connector just reviewed:

> **Connected:** [tool and scope]
> **Test completed:** [task and result]
> **What worked:** [one sentence]
> **Enabled actions:** [actions that remain available]
> **Tools and token-context effect:** [tool count if visible; displayed token impact if available, otherwise LOW / MEDIUM / HIGH effect and why]
> **What to watch:** [permissions, accuracy, privacy, or prompt-injection concern]
> **Keep or disconnect:** [recommendation and why]
> **Next safe step:** [one optional follow-up]

Then show a concise summary of every active connection, including the one just reviewed:

| Connector | Real job | Account access and enabled actions | Tools and token-context effect | Keep, change, or disconnect |
|---|---|---|---|---|

If I cannot name the job a connector supports, or it no longer saves enough work to justify its access or context cost, recommend disconnecting it.

## Example

Someone wants to prepare for tomorrow's meeting without copying event details into chat. They review their calendar connector: its job is to show tomorrow's meetings and the notes they personally added. They keep read access, disable write actions when the app offers that control, inspect the available tool list, and record whether its context cost is still worth the time it saves. They do not connect a mailbox simply because it might contain more context.
