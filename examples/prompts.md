# Side-chat prompts

Run your terminal agent in the same repo T3 Code is working in. These all work as plain requests; prefix with `/t3-side-chat` to call the skill explicitly.

## Catch up

```
catch me up on the Refactor auth chat in T3
what's the T3 agent working on right now?
summarize the chat I'm in — goal, decisions, what's left
```

## Review what the T3 agent did

```
what commands did the agent in "Refactor auth" run, and did any fail?
review the files the T3 agent changed in Refactor auth against git diff
the T3 agent says the tests pass — verify that
```

## Second opinion

```
the T3 agent proposed a migration plan in Refactor auth — poke holes in it
read the last 10 messages of Refactor auth; is its approach to token refresh sound?
```

## Parallel work

```
the T3 agent is on the API side in Refactor auth — write the docs for those changes, don't touch src/
read Refactor auth and draft the PR description for what it's done
```

## Find things across chats

```
search my T3 chats for "rate limit"
which T3 chat did we decide on the retry policy in?
list my T3 projects
list chats in my-api
```

## By link

Copy a thread link from T3 and paste it in:

```
read t3-thread://v2/<environment-id>/<thread-id> and tell me what it decided
```
