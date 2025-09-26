import os
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from httpx import Headers
from mcp.server.fastmcp import FastMCP

from utils.frame_utils import (
    filter_event_driven_frames,
    filter_power_spike_frames,
    get_strategic_frame_subset,
)

load_dotenv()
mcp = FastMCP("riot")
base_url = "https://americas.api.riotgames.com"


async def make_riot_request(url: str) -> Optional[Dict[str, Any]]:
    headers = Headers({"X-Riot-Token": os.getenv("RIOT_API_KEY")})  # type: ignore

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None


async def get_puuid_by_summoner(summoner_name: str, summoner_tagline: str) -> str:
    """Get the puuid of a summoner by summoner name and tagline

    Args:
        summoner_name: Summoner Name
        summoner_tagline: Summoner Tagline

    Returns:
        str: puuid for the given Summoner Name and Tagline
    """
    url = f"{base_url}/riot/account/v1/accounts/by-riot-id/{summoner_name}/{summoner_tagline}"
    response = await make_riot_request(url)

    if response is None:
        return "Error from API"

    return response["puuid"]


@mcp.tool()
async def get_matches_by_summoner(
    summoner_name: str, summoner_tagline: str
) -> Optional[Dict[str, Any]]:
    """Get list of match ids for a summoner name and tagline.

    Args:
        summoner_name: Summoner Name
        summoner_tagline: Summoner Tagline

    Returns:
        dict: Dictionary with a list of match ids.
    """
    puuid = await get_puuid_by_summoner(summoner_name, summoner_tagline)
    url = f"{base_url}/lol/match/v5/matches/by-puuid/{puuid}/ids"
    return await make_riot_request(url)  # type: ignore


@mcp.tool()
async def get_match_details(match_id: str) -> Optional[Dict[str, Any]]:
    """Get all the details available for a given match.

    Args:
        match_id: Match ID that you want details of

    Returns:
        dict: Dictionary with all the details of a given match
    """
    url = f"{base_url}/lol/match/v5/matches/{match_id}"
    return await make_riot_request(url)  # type: ignore


@mcp.tool()
async def get_match_timeline(
    match_id: str, filter_strategy: str = "power_spikes"
) -> List[Dict[str, Any]]:
    """Get the timeline of a given match with optional filtering.

    This gives more details than the `get_match_details` method. Giving detail for each frame of a match.
    Now supports multiple filtering strategies for optimized analysis.

    Args:
        match_id: Match ID that you want details of
        filter_strategy: Filtering strategy for timeline data. Options:
            - "all": Returns the last 55% of frames.
            - "events": Returns frames containing significant events.
            - "power_spikes": Returns frames around champion power spikes. (Default)
            - "strategic": Returns frames with macro-level decisions.

    Filter Strategy Usage Guide:
        - Use "all" for: Full end of match data. This is a lot of data and should be used with caution.
        - Use "events" for: Kill tracking, objective control analysis, highlight generation
        - Use "power_spikes for: Campion performance analysis
        - Use "strategic" for: Macro gameplay analysis objective priority

    Returns:
        List[Dict[str, Any]]: List of timeline frames based on selected strategy
    """
    url = f"{base_url}/lol/match/v5/matches/{match_id}/timeline"
    response = await make_riot_request(url)  # type: ignore
    if response is None:
        return []

    frames = response["info"]["frames"]

    if filter_strategy == "events":
        return filter_event_driven_frames(frames)
    elif filter_strategy == "power_spikes":
        return filter_power_spike_frames(frames)
    elif filter_strategy == "strategic":
        return get_strategic_frame_subset(frames)
    else:
        return frames[int(len(frames) * 0.55) :]


if __name__ == "__main__":
    mcp.run(transport="stdio")
