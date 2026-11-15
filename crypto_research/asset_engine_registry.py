from __future__ import annotations

"""Asset-oriented independent strategy registry.

Each (symbol, strategy_id) is a separate strategy stream with its own signal,
position state, fills, costs, metrics and trade ledger. The registry is not an
ensemble: there is no voting, confirmation, shared entry filter or priority.

M3 implementations live in the separate Model 3 research repository. This
registry records the exact adapter contract but deliberately does not invent
or copy their source code into this repository.
"""

ASSET_ENGINES = {
    "BTCUSDT": {
        "primary": {"strategy_id": "M3_RANK7", "family": "Model3", "adapter": "external_model3_adapter", "status": "historical_candidate", "reported_pf": 1.515, "reported_trades": 175, "period": "2024-2026"},
        "additional": [
            {"strategy_id": "M6_DONCHIAN", "family": "M6", "adapter": "crypto_research.independent_models", "status": "research_candidate"},
            {"strategy_id": "M8_VOL_EXPANSION", "family": "M8", "adapter": "crypto_research.independent_models", "status": "research_candidate"},
        ],
    },
    "ETHUSDT": {
        "primary": {"strategy_id": "M6_4H", "family": "M6", "adapter": "crypto_research.independent_models", "status": "historical_candidate", "reported_pf": 1.7288, "reported_trades": 93, "period": "2024-2025"},
        "additional": [
            {"strategy_id": "M8_1H_RR4", "family": "M8", "adapter": "crypto_research.variant_discovery", "status": "oos_candidate", "reported_pf": 1.4504, "reported_trades": 89, "period": "2025"},
            {"strategy_id": "M3_ETH_ASSET_DISCOVERY", "family": "Model3", "adapter": "external_model3_adapter", "status": "awaiting_exact_asset_profile"},
        ],
    },
    "SOLUSDT": {
        "primary": {"strategy_id": "M3B", "family": "Model3", "adapter": "external_model3_adapter", "status": "historical_candidate", "reported_pf": 2.03, "reported_trades": 1164, "period": "2024"},
        "additional": [
            {"strategy_id": "M6_DONCHIAN", "family": "M6", "adapter": "crypto_research.independent_models", "status": "research_candidate"},
            {"strategy_id": "M8_VOL_EXPANSION", "family": "M8", "adapter": "crypto_research.independent_models", "status": "research_candidate"},
        ],
    },
    "DOGEUSDT": {
        "primary": {"strategy_id": "M3C", "family": "Model3", "adapter": "external_model3_adapter", "status": "historical_candidate_needs_full_period_validation", "reported_pf": 2.66, "reported_trades": 385, "period": "2026_YTD"},
        "additional": [
            {"strategy_id": "M6_DONCHIAN", "family": "M6", "adapter": "crypto_research.independent_models", "status": "doge_research_queued"},
            {"strategy_id": "M8_VOL_EXPANSION", "family": "M8", "adapter": "crypto_research.independent_models", "status": "doge_research_queued"},
        ],
    },
    "ADAUSDT": {
        "primary": {"strategy_id": "M3A", "family": "Model3", "adapter": "external_model3_adapter", "status": "historical_candidate", "reported_pf": 2.35, "reported_trades": 564, "period": "2024"},
        "additional": [
            {"strategy_id": "M6_DONCHIAN", "family": "M6", "adapter": "crypto_research.independent_models", "status": "research_candidate"},
            {"strategy_id": "M8_VOL_EXPANSION", "family": "M8", "adapter": "crypto_research.independent_models", "status": "research_candidate"},
        ],
    },
    "LINKUSDT": {
        "primary": {"strategy_id": "M3C", "family": "Model3", "adapter": "external_model3_adapter", "status": "historical_candidate", "reported_pf": 2.35, "reported_trades": 461, "period": "2025"},
        "additional": [
            {"strategy_id": "M6_DONCHIAN", "family": "M6", "adapter": "crypto_research.independent_models", "status": "research_candidate"},
            {"strategy_id": "M8_VOL_EXPANSION", "family": "M8", "adapter": "crypto_research.independent_models", "status": "research_candidate"},
        ],
    },
    "XRPUSDT": {
        "primary": {"strategy_id": "M3X", "family": "Model3", "adapter": "external_model3_adapter", "status": "historical_candidate", "reported_pf": 1.58, "reported_trades": 345, "period": "2026_YTD"},
        "additional": [
            {"strategy_id": "M6_DONCHIAN", "family": "M6", "adapter": "crypto_research.independent_models", "status": "research_candidate"},
            {"strategy_id": "M8_VOL_EXPANSION", "family": "M8", "adapter": "crypto_research.independent_models", "status": "research_candidate"},
        ],
    },
}

# M6 and M8 are the two additional candidate families. Their profiles remain
# per-symbol parameters selected only from each strategy's own training data.
ADDITIONAL_MODEL_FAMILIES = ("M6", "M8")

ENGINE_CONTRACT = {
    "execution": "completed-bar signal, next-bar-open fill",
    "accounting": "entry/exit fees, slippage and actual perpetual funding",
    "collision": "stop-first when stop and target occur in the same OHLC bar",
    "data_gaps": "invalidate affected trades; never bridge missing intervals",
    "independence": "one position/trade ledger per asset and strategy; no voting",
    "selection": "training-only per-asset/per-model selection; chronological OOS validation",
    "portfolio": "risk allocator may cap aggregate exposure but cannot alter model signals",
}
