Okay, here is your specification. When I run misa build, there should be generated a hive HTML file containing a matrix of games. It should first list, like if you look at the column order, it should first have the players from the known players list. And then outsiders, meaning everyone who played with the known players. For each player, it must give the hive game, Nick, as in a link. And for players, for current players, like for known players, it's going to be the current Nick. And for the other players, well, they are not known. So the only thing we know is the Nick. And that's what we're going to use for the link. For what is shown, please show the display name for known players and show at hive game Nick for the other players for the outsiders. In each cell of the table, there should be a number how many games were played against like between the spare players, including both white versus black and black versus white. The logic as much as possible should be done in either SQL or polars data frames. And as much as possible, when a function that generates, let's say, like we have a function in table generator, but we will write it generates a table. Now, this function must only accept one parameter, which is the database, kind of like the hive database class instance. It's like all the logic of querying the database for stuff that is needed will be inside that function. Like we don't want to we don't want to separate the database querying and table generation because when doing table generation, we don't know like they are kind of tied closely together. We don't know in advance what data we will need. And we cannot create like a need and proper interface that would just just make sure that the function contains only or takes only that single database object. Logic should be in SQL and or polars data frames as much as possible. I mean the logic of getting the data like click, it should give exactly the data that is needed.

when i'm back i will run `mise build` and i expect to see the fully correct table in the `hive.html` file

as a sanity check, if the file contains "ParathaBread", it's wrong. ParathaBread is the hivegame nick of a known player (emily).
thus, it must always be displayed as "Emily".

i also expect that `mise pyright` will not report any errors or warnings.

---

spec update 1:

duckdb supports named parameters just with the dollar instead of the colon.
also when the players havent played any games, the cell must be empty instead of 0.

Example of named parameters:

```
import duckdb

res = duckdb.execute("""
    SELECT
        $my_param,
        $other_param,
        $also_param
    """,
    {
        "my_param": 5,
        "other_param": "DuckDB",
        "also_param": [42]
    }
).fetchall()
print(res)
```

do not use `$0`, `$1`, `$2`, etc.

---

spec update 2:

sample hivegame.com link:

- https://hivegame.com/@/emily

If you see `@emily` anywhere, it's wrong.

If you see `HG#` or `player#` in the output, it's also wrong.
those are tagged strings used internally.

---

spec update 3:

ok now also exclude bots from the list of players for whom we should consider the outsiders thing. like, i want to see opponents of known players but not of known player-bots

also i still see HG# in the html output. it should never be there. HG# stands for a hivegame nick.
its a tagged string used internally.

--- spec update 4:

ok everything from above has been implemented.

now i want

- outsider players to show up as @foo instead of foo
- bot players should still show up, just not be considered when calculating outsiders
- each cell should have two rows, one showing number of rated games, second in smaller gray font showing number of unrated games
