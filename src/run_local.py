from fc.api import FC26_API

api = FC26_API()

# Search returns the single best match as a one-row DataFrame
club = api.search_club_by_name("kcanton")
if club is None:
    raise SystemExit("search failed")
if club.empty:
    raise SystemExit("no club with that name")

club_id = club["clubId"].iat[0]   # e.g. 240

details = api.get_club_details(club_id)                       # transposed DataFrame
matches = api.get_club_matches_normalized(club_id, "leagueMatch")


details.to_csv(r"data\club_details.csv", index=False)
matches.to_csv(r"data\club_matches.csv", index=False)
print(details)
print(matches.head())