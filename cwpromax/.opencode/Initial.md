# PowerKPI Workspace Flow

Use this flow at the start of every session.

## Session Start Behavior

1. First message must be:
	welcome user, you're now in PowerKPI workspace

2. Ask the user who they are.
	- User folders are under: C:\PowerKPI_AI\Workspace
	- Match the entered name to the most related existing folder.
	- Ignore non-user folders such as General.

3. If no user match is found:
	- Ask whether they want to create a new user folder.
	- If yes, create:
	  - C:\PowerKPI_AI\Workspace\<NewUser>
	  - C:\PowerKPI_AI\Workspace\<NewUser>\experience.md
	- Initialize the new experience.md using the template in this file.

4. If an existing user is selected:
	- Open C:\PowerKPI_AI\Workspace\<User>\experience.md
	- Read past entries and summarize relevant context before starting debug work.

---

# Experience Log Template

This template is used for each user's experience.md.

## How to Use

- Add a new entry whenever a new error appears.
- Capture the symptoms, suspected cause, actual root cause, and the debug steps that worked.
- Keep entries concise but actionable so they can be reused later.

## Error Entry Template

### Error Title
- Date:
- Area / File:
- Trigger:
- Symptoms:
- Root Cause:

### Debug Procedure
1. Reproduce the error.
2. Collect logs, stack traces, and related context.
3. Identify the failing component or code path.
4. Test the fix.
5. Record the final resolution.

### Resolution
- Fix Applied:
- Verification:
- Notes:
