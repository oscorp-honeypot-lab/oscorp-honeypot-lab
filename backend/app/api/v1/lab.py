from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.dependencies import get_lab_service, require_role, require_role_csrf
from app.api.schemas import LabRunRequest, LabRunResponse
from app.application.lab_service import (
    LabEnvironmentRequired,
    LabRunConflict,
    LabScenarioInvalid,
    LabService,
)
from app.domain.identity import Role, UserIdentity

router = APIRouter(prefix="/lab", tags=["lab"])
Viewer = Annotated[UserIdentity, Depends(require_role(Role.VIEWER))]
AnalystCsrf = Annotated[UserIdentity, Depends(require_role_csrf(Role.ANALYST))]
Service = Annotated[LabService, Depends(get_lab_service)]


@router.post("/run", status_code=status.HTTP_202_ACCEPTED, response_model=LabRunResponse)
async def start_lab_run(
    body: LabRunRequest,
    actor: AnalystCsrf,
    service: Service,
) -> LabRunResponse:
    try:
        run = await service.start_run(scenario=body.scenario, actor=actor.username)
    except LabEnvironmentRequired as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="lab_environment_required",
        ) from exc
    except LabScenarioInvalid as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="lab_scenario_invalid",
        ) from exc
    except LabRunConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="lab_run_conflict",
        ) from exc
    return LabRunResponse.from_domain(run)


@router.get("/status", response_model=LabRunResponse)
async def get_lab_status(
    _: Viewer,
    service: Service,
) -> Response:
    run = await service.get_status()
    if run is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return LabRunResponse.from_domain(run)


@router.get("/logs/{run_id}", response_class=Response)
async def get_lab_logs(
    run_id: int,
    _: Viewer,
    service: Service,
) -> Response:
    log_text = await service.get_logs(run_id=run_id)
    return Response(
        content=log_text,
        media_type="text/plain; charset=utf-8",
    )
