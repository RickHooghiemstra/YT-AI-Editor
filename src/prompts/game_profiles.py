"""
Per-game context injected into analyzer and scriptwriter prompts.
Fuzzy-matches the user's game name to a known profile.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Optional


@dataclass
class GameProfile:
    name: str
    aliases: list[str] = field(default_factory=list)
    genre: str = "action"
    key_moments: list[str] = field(default_factory=list)
    terminology: dict[str, str] = field(default_factory=dict)
    audience_notes: str = ""
    content_style: str = ""
    typical_highlight_duration: int = 20  # seconds

    def context_block(self) -> str:
        terms = ", ".join(f"{k} ({v})" for k, v in self.terminology.items())
        moments = ", ".join(self.key_moments)
        return (
            f"Game: {self.name} ({self.genre})\n"
            f"Key moments to watch for: {moments}\n"
            f"Terminology: {terms}\n"
            f"Audience: {self.audience_notes}\n"
            f"Content style: {self.content_style}"
        )


_PROFILES: list[GameProfile] = [
    GameProfile(
        name="Valorant",
        aliases=["val", "valo"],
        genre="tactical FPS",
        key_moments=[
            "ace (kill entire enemy team)", "clutch (1vX)", "spike plant/defuse",
            "eco round win", "flawless round", "operator one-tap", "knife kill",
            "impossible angle kill", "perfect utility usage",
        ],
        terminology={
            "ace": "killing all 5 enemies",
            "clutch": "winning a round while outnumbered",
            "eco": "round played with minimal money",
            "spike": "the bomb",
            "operator": "high-powered sniper rifle",
        },
        audience_notes="Competitive FPS players, aged 16–28, respond strongly to mechanical skill and clutch moments",
        content_style="Fast cuts, reaction cam on big moments, utility/crosshair placement explanations for tutorials",
        typical_highlight_duration=25,
    ),
    GameProfile(
        name="CS2",
        aliases=["counter-strike", "csgo", "cs go", "cs:go", "cs 2", "counter strike"],
        genre="tactical FPS",
        key_moments=[
            "ace", "clutch", "AWP no-scope", "deagle headshot", "bomb plant/defuse",
            "eco win", "pistol round win", "knife round", "multi-kill",
        ],
        terminology={
            "ace": "killing all 5 enemies",
            "AWP": "high-powered sniper rifle",
            "deagle": "Desert Eagle pistol",
            "eco": "round played with minimal buy",
            "T-side": "attacking team",
            "CT-side": "defending team",
        },
        audience_notes="Hardcore FPS players who appreciate game sense and mechanics over flashy plays",
        content_style="Clean crosshair placement, utility lineups for tutorials; hype edits for highlights",
        typical_highlight_duration=20,
    ),
    GameProfile(
        name="Minecraft",
        aliases=["mc", "mine craft"],
        genre="sandbox / survival",
        key_moments=[
            "death (especially ironic/funny ones)", "first diamond find", "first nether portal",
            "end boss fight", "creeper explosion fail", "massive build reveal",
            "speedrun milestone", "raid defeat", "impressive redstone activation",
        ],
        terminology={
            "creeper": "explosive mob that sneaks up on players",
            "Ender Dragon": "final boss",
            "netherite": "highest-tier material",
            "speedrun": "completing the game as fast as possible",
        },
        audience_notes="Broad audience from children to adults; nostalgia-driven, respond to both skill and humour",
        content_style="Reactions and storytelling matter as much as gameplay; timelapse for builds, real-time for combat",
        typical_highlight_duration=30,
    ),
    GameProfile(
        name="Fortnite",
        aliases=["fortnite br", "fn"],
        genre="battle royale",
        key_moments=[
            "Victory Royale", "multi-kill", "building outplay", "last-circle 1v1",
            "no-build clutch", "snipe from distance", "box fight win", "creative edit",
        ],
        terminology={
            "Victory Royale": "winning the match",
            "storm": "shrinking zone that damages players outside it",
            "building": "constructing structures in-game",
            "box fight": "close-range fight inside player-built structures",
        },
        audience_notes="Young audience (12–22), highly visual, respond to fast edits and trend-relevant content",
        content_style="Very fast cuts, overlaid sound effects, trend-aware titles and captions",
        typical_highlight_duration=15,
    ),
    GameProfile(
        name="League of Legends",
        aliases=["lol", "league", "lol game"],
        genre="MOBA",
        key_moments=[
            "pentakill", "1v5 outplay", "Baron steal", "Dragon soul secured",
            "turret dive kill", "perfect ult usage", "late-game teamfight win",
            "come-from-behind victory",
        ],
        terminology={
            "pentakill": "killing all 5 enemies quickly",
            "Baron": "powerful neutral monster that buffs team",
            "gank": "unexpected attack from off-screen",
            "ult": "ultimate ability (most powerful skill)",
            "CS": "creep score (minions killed for gold)",
        },
        audience_notes="Dedicated MOBA players who respect macro strategy; pentakills and outplays go viral",
        content_style="Highlight teamfights and solo outplays; commentate decision-making for tutorials",
        typical_highlight_duration=35,
    ),
    GameProfile(
        name="Apex Legends",
        aliases=["apex", "apex legends br"],
        genre="battle royale FPS",
        key_moments=[
            "squad wipe", "Ranked Predator", "legend ability outplay",
            "third-party survival", "final ring 1v3", "banner retrieve under fire",
            "no-scope kill", "revive under pressure",
        ],
        terminology={
            "squad wipe": "eliminating the entire enemy team",
            "banner": "item retrieved to respawn a teammate",
            "third-party": "attacking a team already in a fight",
            "ring": "shrinking zone",
        },
        audience_notes="High-skill FPS audience who value movement tech and team coordination",
        content_style="Movement clips and ability combinations perform extremely well; team communication audio adds value",
        typical_highlight_duration=25,
    ),
    GameProfile(
        name="Call of Duty",
        aliases=["cod", "warzone", "mw", "modern warfare", "black ops", "cold war", "mwii", "mwiii"],
        genre="FPS / battle royale",
        key_moments=[
            "nuke", "multi-kill", "long-range snipe", "helicopter takedown",
            "Warzone Victory", "clutch revive", "killstreak activation", "melee kill",
        ],
        terminology={
            "nuke": "killstreak that ends the match",
            "Warzone": "battle royale mode",
            "gulag": "1v1 match for a chance to respawn",
            "UAV": "killstreak that reveals enemy positions",
        },
        audience_notes="Mainstream gaming audience; casual to hardcore; big reactions and spectacle perform well",
        content_style="High-energy edits, big sound design, speed-ramped kills",
        typical_highlight_duration=20,
    ),
    GameProfile(
        name="Overwatch",
        aliases=["ow", "ow2", "overwatch 2"],
        genre="hero shooter",
        key_moments=[
            "team wipe with ultimate", "Genji blade", "Pharah ult", "Lucio boop into pit",
            "clutch Mercy rez", "environmental kill", "perfect counter-ult",
            "spawn camp escape",
        ],
        terminology={
            "ult": "ultimate ability",
            "rez": "Mercy's resurrect ability",
            "boop": "knockback attack",
            "dive": "aggressive flanking strategy",
        },
        audience_notes="Casual-to-midcore audience; hero-specific fans respond to mains highlights",
        content_style="Show the lead-up to ultimates so the payoff lands; reactions from teammates add humour",
        typical_highlight_duration=25,
    ),
    GameProfile(
        name="Rocket League",
        aliases=["rl", "rocket league game"],
        genre="vehicular soccer",
        key_moments=[
            "aerial goal", "bicycle kick goal", "ceiling shot", "demo chain",
            "overtime winner", "impossible save", "0-second goal", "mechanical outplay",
        ],
        terminology={
            "aerial": "jumping and boosting in the air to hit the ball",
            "demo": "ramming and destroying an opponent's car",
            "ceiling shot": "bouncing off the ceiling to score",
            "flip reset": "advanced mechanic resetting jump in mid-air",
        },
        audience_notes="Mechanically focused players; skill ceiling is very high so impressive plays get strong reactions",
        content_style="Slow-motion replay on insane shots; keep reaction cam prominent for goal celebrations",
        typical_highlight_duration=12,
    ),
    GameProfile(
        name="Forza Horizon",
        aliases=["forza", "fh5", "fh4", "forza motorsport", "forza horizon 5", "forza horizon 4"],
        genre="racing / open world",
        key_moments=[
            "perfect drift chain", "near-miss at top speed", "impossible overtake",
            "Danger Sign jump record", "Speed Trap world record", "photo mode stunning shot",
            "Barn Find reveal", "Festival Playlist win", "online elimination victory",
        ],
        terminology={
            "Barn Find": "hidden classic car discovered in a barn",
            "Danger Sign": "jump challenge with distance targets",
            "Speed Trap": "speed measurement checkpoint",
            "Goliath": "longest race in the game",
            "drift": "controlled sideways slide through corners",
        },
        audience_notes="Car enthusiasts and casual racers; stunning scenery and extreme speed resonate; tune builds and car reveals perform well",
        content_style="Cinematic wide shots during drifts and jumps; highlight tune builds for car fans; reaction cam on record-breaking moments",
        typical_highlight_duration=20,
    ),
    GameProfile(
        name="World of Warcraft",
        aliases=["wow", "wow classic", "world of warcraft classic", "wow retail", "classic wow"],
        genre="MMORPG",
        key_moments=[
            "raid boss kill", "Mythic+ dungeon timed clear", "PvP kill streak",
            "rare item drop", "Achievement unlock", "world first clear",
            "close wipe save", "unexpected come-from-behind victory",
        ],
        terminology={
            "raid": "large group PvE encounter (10–25 players)",
            "Mythic+": "timed high-difficulty dungeon",
            "wipe": "entire group dying and resetting the encounter",
            "loot": "equipment dropped by bosses",
            "DPS": "damage-dealing role",
            "tank": "damage-absorbing front-line role",
            "healer": "support role keeping the group alive",
        },
        audience_notes="Dedicated MMORPG community; responds to progression milestones, loot reveals, and guild moments",
        content_style="Show raid coordination and boss mechanics for tutorials; reaction cam essential on boss kills and rare drops",
        typical_highlight_duration=40,
    ),
    GameProfile(
        name="Guild Wars 2",
        aliases=["gw2", "guild wars", "guildwars 2", "guildwars2"],
        genre="MMORPG",
        key_moments=[
            "World vs World siege victory", "Fractals boss kill", "Raid clear",
            "Legendary item craft reveal", "1vX WvW fight", "strike mission clear",
            "jumping puzzle completion", "Dragon Strikes event win",
        ],
        terminology={
            "WvW": "World vs World — large-scale open PvP between servers",
            "Fractals": "instanced endgame dungeons with increasing difficulty scales",
            "Legendary": "highest-tier cosmetic/stat equipment",
            "downstate": "downed but not dead — can be revived",
            "zerg": "large group of players moving together in WvW",
        },
        audience_notes="Community-focused players who appreciate exploration and cosmetics as much as combat; WvW and endgame raids attract dedicated fans",
        content_style="Show large-scale WvW battles with context; Legendary reveals get strong reactions; keep explanation concise for skill-based moments",
        typical_highlight_duration=35,
    ),
    GameProfile(
        name="Zoo Tycoon",
        aliases=["zoo tycoon ultimate", "zoo tycoon 2", "planet zoo"],
        genre="management / simulation",
        key_moments=[
            "animal habitat reveal", "rare species birth", "visitor milestone",
            "perfect enclosure rating", "animal escape moment", "conservation goal achieved",
            "zoo expansion reveal", "five-star rating unlock",
        ],
        terminology={
            "habitat": "enclosure designed for a specific animal",
            "conservation": "in-game system rewarding animal welfare",
            "biome": "environmental type matching animal's natural habitat",
        },
        audience_notes="Casual simulation fans and wildlife enthusiasts; satisfying build reveals and cute animal moments perform well",
        content_style="Timelapse for construction phases; real-time for animal behaviour and reactions; warm positive tone throughout",
        typical_highlight_duration=30,
    ),
    GameProfile(
        name="Jurassic World Evolution",
        aliases=["jwe", "jurassic world evolution 2", "jwe2", "jurassic park game", "jurassic evolution"],
        genre="management / simulation",
        key_moments=[
            "dinosaur breakout", "new species hatchery reveal", "guest panic moment",
            "dinosaur fight", "record-breaking park rating", "bioengineered genome unlock",
            "storm survival", "Raptor squad formation",
        ],
        terminology={
            "genome": "dinosaur DNA completeness percentage",
            "enclosure": "fenced habitat for dinosaurs",
            "ranger": "NPC team managing dinosaur health",
            "hatchery": "facility for creating new dinosaurs",
            "biosyn": "genetics faction in JWE2",
        },
        audience_notes="Jurassic Park fans and simulation players; chaos moments (breakouts, fights) get the strongest reactions; build reveals and species unlocks perform well",
        content_style="Reaction cam essential on breakout moments; dramatic music hits; timelapse for park construction; lean into the film's cinematic style",
        typical_highlight_duration=25,
    ),
]

_GENERIC = GameProfile(
    name="Unknown Game",
    aliases=[],
    genre="video game",
    key_moments=[
        "impressive skill display", "close-call survival", "funny fail or death",
        "victory moment", "unexpected event", "achievement unlock",
    ],
    terminology={},
    audience_notes="General gaming audience",
    content_style="Highlight the most visually dramatic moments; reactions carry the edit",
    typical_highlight_duration=20,
)


def get_game_profile(game_name: str) -> GameProfile:
    """Fuzzy-match game name to a known profile. Returns generic if no match."""
    query = game_name.lower().strip()

    # Exact alias match first
    for profile in _PROFILES:
        if query == profile.name.lower() or query in profile.aliases:
            return profile

    # Fuzzy match on name and aliases
    best_score = 0.0
    best_profile: Optional[GameProfile] = None
    for profile in _PROFILES:
        candidates = [profile.name.lower()] + profile.aliases
        for candidate in candidates:
            score = SequenceMatcher(None, query, candidate).ratio()
            if score > best_score:
                best_score = score
                best_profile = profile

    if best_score >= 0.6 and best_profile:
        return best_profile

    generic = GameProfile(
        name=game_name,
        aliases=[],
        genre="video game",
        key_moments=_GENERIC.key_moments,
        terminology={},
        audience_notes=_GENERIC.audience_notes,
        content_style=_GENERIC.content_style,
        typical_highlight_duration=_GENERIC.typical_highlight_duration,
    )
    return generic
