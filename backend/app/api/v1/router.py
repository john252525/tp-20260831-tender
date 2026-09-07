from fastapi import APIRouter
from app.api.v1 import system, tokens, settings, categories, tasks, tender_sources, tenders, suppliers, communications, commercial_offers, decisions, negotiations

api_router = APIRouter()
api_router.include_router(system.router, tags=['System'])
api_router.include_router(tokens.router, prefix='/tokens', tags=['Tokens'])
api_router.include_router(settings.router, prefix='/settings', tags=['Settings'])
api_router.include_router(categories.router, prefix='/categories', tags=['Categories'])
api_router.include_router(tasks.router, prefix='/tasks', tags=['Tasks'])
api_router.include_router(tender_sources.router, prefix='/tender-sources', tags=['TenderSources'])
api_router.include_router(tenders.router, prefix='/tenders', tags=['Tenders'])
api_router.include_router(suppliers.router, prefix='/suppliers', tags=['Suppliers'])
api_router.include_router(communications.router, prefix='/tenders', tags=['Communications'])
api_router.include_router(commercial_offers.router, prefix='/commercial-offers', tags=['Communications'])
api_router.include_router(decisions.router, prefix='/decisions', tags=['Decisions'])
api_router.include_router(negotiations.router, tags=['Negotiations'])
