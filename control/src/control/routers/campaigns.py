"""Campaign lifecycle endpoints."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, status

from emfi_protocol.campaigns import Campaign, CampaignStatus

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("", response_model=CampaignStatus)
async def start(campaign: Campaign) -> CampaignStatus:
    """Start a campaign. Returns immediately with the assigned ID."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.get("", response_model=List[CampaignStatus])
async def list_all() -> List[CampaignStatus]:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.get("/{campaign_id}", response_model=CampaignStatus)
async def get_one(campaign_id: str) -> CampaignStatus:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")


@router.post("/{campaign_id}/stop")
async def stop(campaign_id: str) -> dict:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="TODO")
