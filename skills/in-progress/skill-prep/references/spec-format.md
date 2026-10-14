# Spec format

One Markdown file with four parts, in this order: Run, Checks run, Items, Could not check.

Every item proposes a change. A match that needs no change stays out of Items.

The spec quotes the text in the folder that needs to change, so it is private. Write it outside the audited folder, and by default outside any git repository. A path the user chooses wins; warn the user when that path sits inside a repository.

## Template

````markdown
# Spec: <folder name>

## Run
- Folder audited: <path>
- Original compared: <path, or none>
- Destination: <path or URL, or none>
- Destination conventions: <layout, naming, catalog entry shape, link style> (when a destination was given)
- Guidance used: <each link, marked fetched or could not fetch; or "light fallback basics">
- Stance: <agnostic, or fitted to a named model or harness> because <evidence>
- Fit per target: <target>: <item ids> (when there are several targets)
- Matches kept: <where>: <reason> (matches judged to need no change)
- Removed by review: <item id>: <reason> (items the review removed)
- Git history: <note> (when the folder sits in a repository with a remote)
- Discovery: <what the conversation held, which instruction and memory files were read, which areas were scanned, which candidates were disclosed to the user and opened>

## Checks run
| # | Check | Result |
| --- | --- | --- |
| 1 | Private references | ran, found 2 |
| 2 | Own workflow | ran, found 0 |
| 3 | History | could not check, <reason> |

## Items

### 01. Private references (mechanical)
Where: SKILL.md:42
Found: "<the exact text>"
Change: <the exact replacement, or "delete the line">
Why: <the rule, with the guidance link or the workspace item that raised it>

### 02. Own workflow (recommendation)
Where: references/process.md:10
Found: "<the exact text>"
Options:
- A. <option> (recommended)
- B. <option>
Why: <the rule, with the guidance link or the workspace item that raised it>

## Could not check
- <check, file or link>: <reason>
````

## Fields

- **Where.** The file and line. Use the line range when the text spans several lines. For work done outside the folder, write `outside the folder`.
- **Found.** The exact text. Quote enough to find it again after other edits.
- **Change.** Mechanical items carry the exact replacement, or say to delete. A mechanical item has one correct edit and needs no judgment from the user.
- **Options.** Recommendations replace Change with two or three options and mark one as recommended. These are the user's decisions. Each option is a change to the folder, to an input the user supplies, or to work done outside the folder. A match that may stay as it is is not an item.
- **Why.** Name the rule, link the guidance when it comes from the guidance, and name the workspace item when the match came from discovery.
- **Review.** Items the adversarial review added or changed carry a final line `Review: <what changed and why>`.
- **Could not check.** Lists a check that was unable to run, with the reason. An optional step that does not apply because its input was not supplied, and a review the user declined, go under Run.

## Example items

An invented skill named `recipe-scaler`, audited from a folder the user keeps in a project with its own instruction files.

```markdown
### 01. Private references (mechanical)
Where: SKILL.md:18
Found: "Save the result to notes/team-process.md, then tell the reviewer."
Change: "Save the result where the user asks, and tell them where it went."
Why: The path and the role name match a workflow described in the project's instruction files.

### 02. Own workflow (recommendation)
Where: references/scaling.md:6
Found: "Run the review checklist before scaling any batch."
Options:
- A. Replace with "Check the batch size against the user's stated limit." (recommended)
- B. Move the review step into an optional input the user can supply.
- C. Delete the sentence.
Why: The review checklist is a routine described in the project's instruction file. The step reads as part of the skill but exists for one team's habit.
```

## Clean

The spec is clean when Items is empty and Could not check is empty. A check marked could not check keeps the spec from being clean.
