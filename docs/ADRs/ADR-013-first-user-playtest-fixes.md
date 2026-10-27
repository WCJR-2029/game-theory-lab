# ADR-013: Decisions from the first-user playtests
Status: Accepted (2026-10-26)

## Context
Cold "first-time user" sessions (an AI playing a newcomer, an impatient player, a literal reader, a returning player
and a deliberate breaker) were run against the Lab several times, with fixes in between. Most findings were bugs and
were fixed under tests. The ones below changed how a game plays or looks, so they are recorded here.

## Decisions

### 1. Dictator rounds on both sides (amends ADR-010)
- **Problem.** The Phase 5 spec promised "Dictator rounds that expose your real generosity", the briefing tells the
  player to "pay attention to what you actually offer when the other side can't say no", and the Dictator nudge asks
  "what did your generosity actually look like?". But the player was only ever the responder in Dictator rounds, so
  that lesson never happened.
- **Decision.** The 8-round session now runs in a cycle of four:
  1. you propose;
  2. you respond;
  3. you decide (Dictator: they can't refuse);
  4. you receive (Dictator).

  The debrief compares the player's own offers in the two kinds of proposer round ("When they could say no, you
  offered X% on average; when they couldn't, Y%"). The numbers come from the session's own log, so they show with
  reputation on or off.
- **Alternatives.** Change the copy to match the old schedule. Rejected: the lesson that matters in Dictator is felt
  only as the one deciding. Keep receiver-only Dictator rounds and add a separate Dictator mode. Rejected as more
  surface for the same lesson.

### 2. The next decision before the teaching note (arena games)
- **Problem.** After each round the screen showed the last result, then the teaching note (a tall card), then the move
  buttons and "Play out this match". Players had to scroll on most rounds to find the next decision; in Stag Hunt the
  Hunt buttons sat off-screen after announcing. "Play out this match" was found only by scrolling and said nothing
  about what it does until hovered.
- **Decision.** Order in the Prisoner's Dilemma, Stag Hunt and Chicken: the last result (one banner), the decision
  with "Play out this match" and a one-line "Finishes this match for you." beside it, then the teaching note. The
  Stag Hunt and Chicken first-round setup notes, set for new players but never shown, now show too.
- **Alternatives.** Decision above the last result: rejected, the result is what the next decision reacts to. Hiding
  the note in an expander for new players: rejected, ADR-005 shows it inline until the player has some experience.

### 3. The debrief says something about your own play (arena games)
- **Problem.** Players kept saying the end of a run "never talks about how I did": beyond a rank, the paragraph covers
  the bots, and nothing said how many rounds Play-out had played for them.
- **Decision.** The result banner carries one line from the run itself: what you chose (Cooperate / Stag / Swerve,
  plus announcements kept in Stag Hunt and wheels thrown in Chicken), how many rounds were played out for you, and
  which opponent you scored most and least against. It counts choices, not what noise turned them into, and makes no
  judgement; the "what just happened" paragraph still names the dynamic.
- **Alternatives.** A per-round history table: rejected, too much for a first-time reader. Advice ("try defecting
  against X"): rejected, constraint 3 (not about winning).

### 4. A next step at the end of every run
- **Problem.** The end of a run offered only "Play again"; players said there was no clear "you're done" or next step.
- **Decision.** Each debrief also offers "Next on the ladder: <game>", following the menu order (the ladder of
  ADR-003); after the last game it offers "Back to the menu". The order is read from the registry, so a new rung
  joins the ladder by being added to the menu.

### 5. Settings lock during a run; an empty pick-list can't start
- **Problem.** Every sidebar setting is read only when a run starts, but changing one mid-run silently did nothing.
  Unticking every opponent still started a game against a hidden default.
- **Decision.** While a run is in progress the sidebar settings are off, with one line saying how to change them;
  they unlock on the debrief, so "Play again" uses the new settings. With nothing picked in a pick-list, Start is off
  with a line saying why; the arena rosters have "Select all" and "Clear".
- **Alternatives.** Apply changes mid-run: rejected, a run's standings would mix two rule sets. A confirmation to
  restart on change: rejected as more interruption than a disabled control that says why.

### 5b. Settings are remembered outside the widgets
- **Problem.** Streamlit forgets a widget's value while it isn't drawn, so leaving a game for the menu reset its
  sidebar settings; mid-run, the locked sidebar then showed settings the run wasn't using. Writing the roster's ticks
  into the checkboxes' own state (for Select all / Clear) could also leave the browser showing them unticked while the
  app counted them ticked, and a Start click then crashed.
- **Decision.** gtlab/ui/settings.py: every sidebar setting lives in its own session-state store and is handed back as
  the widget's starting value; code changes a setting by giving its widget a fresh key, never by writing widget state.
  Start also re-checks the pick-list when clicked. A disabled control can still deliver a click, so every handler
  behind one (Start, Select all / Clear, Lock in) checks its own condition again.

### 6. The menu remembers you
- **Problem.** A player coming back the next day saw the identical menu, with no sign they had been there.
- **Decision.** Each menu card shows "You've played N <matches / puzzles / sessions>" from the anonymous per-game
  counts ADR-005 already keeps; a game not yet played shows nothing. No new data is stored.

### 7. Say what Play-out plays, how long a run is, and what's next
- **Problem.** In a later round four of five players still couldn't tell what "Play out this match" would play (the
  move was only in the tooltip), three didn't know before Start that a run is 6 opponents x 10 rounds, and a returning
  player found no "where to pick up".
- **Decision.** The line beside Play-out names the move ("playing Cooperate each round"). The setup screen says how
  long the run is and that Play-out can finish any match. Once something has been played, the menu marks the first
  game not yet played "Next up". Stag Hunt's and Chicken's second step no longer repeat the first step's prompt, so
  their buttons sit higher.

### 8. A Schelling number is checked by the app, not by the box
- **Problem.** Streamlit never sends the app a number outside a box's bounds; the box keeps showing what was typed.
  A player who typed 7 and then -5 saw -5 and was told "You picked 7". The bounds also came from a rule
  (`hi >= 10,000` means no limit) that caught the negative-numbers puzzle, so 0 (the crowd's favourite) and every
  negative number couldn't be entered there.
- **Decision.** The number boxes carry no bounds of their own. Every typed number reaches the app, which checks it
  against the puzzle's range, names the range when it is outside, and keeps Lock in off. In the bank, a bound of
  exactly +/-10,000 stands for "no limit"; a test holds every such puzzle's prompt to saying so. After lock-in the
  reveal shows the saved pick, not the box's own state.

## Declined
Recorded so they are not re-raised without new evidence.
- **Resuming a run after a browser refresh.** It would mean persisting the whole arena (RNG and opponent state).
  ADR-005 deliberately stores only anonymous per-game counts. A refresh starting over is acceptable for a sandbox.
- **Remembering past results or rosters on the menu.** Same reason: the progress file holds anonymous counts only.
- **A shorter default roster.** The full field is what the arena's standings teach (who did well depends on who was
  there); with the run length stated up front, Play-out, and Select all / Clear, the player sets the length.
- **Thousands separators on Ultimatum's offer slider.** Streamlit's slider format can't add them; the figures under
  the slider show them.
