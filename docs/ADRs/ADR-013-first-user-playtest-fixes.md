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

## Declined
Recorded so they are not re-raised without new evidence.
- **Resuming a run after a browser refresh.** It would mean persisting the whole arena (RNG and opponent state).
  ADR-005 deliberately stores only anonymous per-game counts. A refresh starting over is acceptable for a sandbox.
