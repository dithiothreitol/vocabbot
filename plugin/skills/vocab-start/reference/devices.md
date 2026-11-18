# Devices and the account

## How the record joins

- An account on a VocabBot server is the shared place of the record. A folder
  linked to it (`vocabbot login`) keeps a full copy that works without a
  network: the program fetches from the account before `today`, `next`,
  `drill` and `status`, and sends after every command that writes. Without a
  network the rows wait in the folder and go with the next command.
- Logs only grow on both sides, and the engine reads every log in its own
  order, so the joined rows give one schedule everywhere. The same card
  answered on two devices without a network: the earlier answer moves the due
  date, the later one counts as drill. Two devices without a network may
  together bring in more new words than the plan's number for a day.
- A change of the plan is a row of `log/plan.jsonl`. For every setting the
  latest change holds, so a change made on a phone and another made on a
  computer both stay.
- The plan's `timezone` (an IANA name such as `Europe/Warsaw`) sets the
  learning day on every device and on the server; linking a folder whose plan
  has none gives it the account's zone.
- A folder belongs to one account. When the program is signed in to another
  account of the same server, the synchronisation stops with `other_account`;
  `vocabbot login --again` signs in to the folder's own account.
- Lines the account refuses for a passing reason (this computer's clock ahead
  of the server, a course the server does not have yet) wait in the folder and
  go again with every synchronisation; `status` counts them as waiting.

## Commands

| Command | What it does |
|---|---|
| `vocabbot login [server]` | sign in through the browser and link the folder (a preview), or download the account into a new folder |
| `vocabbot login --code` | the same with a code confirmed on another device, for a computer without a browser |
| `vocabbot login --plan folder` / `--plan account` | whose plan stays when both differ |
| `vocabbot sync` | synchronise now |
| `vocabbot logout` | end this computer's connection and unlink the folder |
| `vocabbot export <file.zip>` | the record as a zip in the form of a learner's folder |
| `vocabbot import <file.zip>` | a new folder from a zip, or the rows a folder lacks (a preview) |

The default server is the one in `vocabbot login --help`; the variable
`VOCABBOT_SERVER` names another.

## The server's pages

- `/app/`: the session in a browser, also on a phone (add it to the home
  screen): the day's cards, progress and the plan, without a chat application
  and without a model.
- `/account`: the connected applications and computers (each can be
  disconnected), the data as a zip, the optional e-mail address for password
  recovery, and removing the account.
- `/device`: where the code of `vocabbot login --code` is confirmed.

## Without an account

A learner's folder in a synced folder (OneDrive, Dropbox) still works on two
computers: `vocabbot use <folder>` points the second computer at it. Rows of
conflict copies count at once; `doctor --merge` tidies the files after a yes.
