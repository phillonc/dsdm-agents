"""
Requirement Parser Module

Transforms natural language queries into structured requirements
that can be used by the FSM Builder and Code Synthesizer.
"""

import re
from typing import Optional, Dict, Any, List
from ..models.schemas import (
    RequirementSpec,
    GenerationContext,
    UserPreferences,
    ExpertiseLevel
)


# Common options trading terms and intents
INTENT_PATTERNS = {
    "options_chain": [
        r"options?\s+chain",
        r"show\s+.*options",
        r"view\s+.*options",
        r"options?\s+for",
        r"calls?\s+and\s+puts?",
    ],
    "greeks_display": [
        r"greeks?",
        r"delta|gamma|theta|vega",
        r"risk\s+metrics",
    ],
    "payoff_diagram": [
        r"payoff",
        r"profit.*loss",
        r"p[&/]?l\s+(chart|diagram|graph)",
        r"risk.*reward",
        r"breakeven",
    ],
    "volatility_surface": [
        r"volatility\s+surface",
        r"iv\s+surface",
        r"3d\s+.*volatility",
        r"vol(atility)?\s+skew",
    ],
    "strategy_builder": [
        r"build.*strategy",
        r"create.*strategy",
        r"(iron\s+condor|butterfly|spread|straddle|strangle|covered\s+call|wheel)",
        r"construct",
    ],
    "strategy_comparison": [
        r"compare.*strateg",
        r"vs\.?\s+",
        r"versus",
        r"which\s+is\s+better",
    ],
    "portfolio_view": [
        r"portfolio",
        r"my\s+positions?",
        r"holdings?",
        r"exposure",
    ],
    "educational": [
        r"explain",
        r"what\s+is",
        r"how\s+does",
        r"teach",
        r"learn",
        r"understand",
        r"tutorial",
    ],
    "earnings_calendar": [
        r"earnings?\s+calendar",
        r"upcoming\s+earnings",
        r"earnings?\s+dates?",
    ],
    "flow_analysis": [
        r"flow",
        r"unusual\s+(options?|activity)",
        r"dark\s+pool",
        r"sweep",
    ],
    "alert_setup": [
        r"alert",
        r"notify",
        r"watch\s+for",
        r"trigger",
    ],
    "gex_analysis": [
        r"gex",
        r"gamma\s+exposure",
        r"dealer\s+position",
        r"pin\s+risk",
    ],
    "quote_view": [
        r"quote",
        r"price",
        r"current\s+value",
        r"ticker",
    ],
}

# Data type patterns
DATA_PATTERNS = {
    "options_chain": [r"options?\s+chain", r"calls?", r"puts?", r"strikes?"],
    "quote": [r"quote", r"price", r"bid", r"ask"],
    "greeks": [r"greek", r"delta", r"gamma", r"theta", r"vega", r"rho"],
    "open_interest": [r"open\s+interest", r"\boi\b", r"volume"],
    "iv": [r"implied\s+volatility", r"\biv\b", r"iv\s+rank", r"iv\s+percentile"],
    "historical": [r"historical", r"history", r"past", r"previous"],
    "flow": [r"flow", r"sweep", r"block", r"unusual"],
    "portfolio": [r"portfolio", r"position", r"holding"],
    "earnings": [r"earnings?", r"report", r"eps"],
    "gex": [r"gex", r"gamma\s+exposure"],
}

# Visualization patterns
VIZ_PATTERNS = {
    "table": [r"table", r"list", r"chain"],
    "chart": [r"chart", r"graph", r"plot"],
    "heatmap": [r"heatmap", r"heat\s+map", r"color.*coded"],
    "diagram": [r"diagram", r"payoff", r"p[&/]?l"],
    "3d": [r"3d", r"surface", r"three.*dimension"],
    "gauge": [r"gauge", r"meter", r"dial"],
    "card": [r"card", r"summary", r"overview"],
    "timeline": [r"timeline", r"calendar", r"schedule"],
    "comparison": [r"side.*by.*side", r"compare", r"versus"],
}

# Interaction patterns
INTERACTION_PATTERNS = {
    "sort": [r"sort", r"order\s+by", r"rank"],
    "filter": [r"filter", r"show\s+only", r"hide", r"highlight"],
    "expand": [r"expand", r"detail", r"drill.*down"],
    "click": [r"click", r"tap", r"select"],
    "hover": [r"hover", r"tooltip", r"mouse.*over"],
    "drag": [r"drag", r"move", r"reorder"],
    "zoom": [r"zoom", r"scale", r"magnif"],
    "toggle": [r"toggle", r"switch", r"show.*hide"],
}


class RequirementParser:
    """
    Parses natural language queries into structured requirements
    for UI generation.
    """

    def __init__(self):
        """Initialize the requirement parser."""
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile regex patterns for efficiency."""
        self._intent_compiled = {
            intent: [re.compile(p, re.IGNORECASE) for p in patterns]
            for intent, patterns in INTENT_PATTERNS.items()
        }
        self._data_compiled = {
            data: [re.compile(p, re.IGNORECASE) for p in patterns]
            for data, patterns in DATA_PATTERNS.items()
        }
        self._viz_compiled = {
            viz: [re.compile(p, re.IGNORECASE) for p in patterns]
            for viz, patterns in VIZ_PATTERNS.items()
        }
        self._interaction_compiled = {
            inter: [re.compile(p, re.IGNORECASE) for p in patterns]
            for inter, patterns in INTERACTION_PATTERNS.items()
        }
        # Symbol pattern (stock tickers)
        self._symbol_pattern = re.compile(
            r'\b([A-Z]{1,5})\b(?!\s*(?:calls?|puts?|options?|chain|greeks?))',
            re.IGNORECASE
        )
        # Common non-ticker words to exclude
        self._non_tickers = {
            'show', 'me', 'the', 'for', 'with', 'and', 'or', 'my', 'all',
            'iv', 'oi', 'atm', 'otm', 'itm', 'exp', 'jan', 'feb', 'mar',
            'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
            'how', 'what', 'why', 'when', 'does', 'can', 'will', 'is',
            'vs', 'get', 'put', 'call', 'add', 'set', 'let', 'see',
        }

    async def parse(
        self,
        query: str,
        context: Optional[GenerationContext] = None,
        preferences: Optional[UserPreferences] = None
    ) -> RequirementSpec:
        """
        Parse a natural language query into structured requirements.

        Args:
            query: Natural language query from user
            context: Optional context (symbol, positions, etc.)
            preferences: Optional user preferences

        Returns:
            RequirementSpec with structured requirements
        """
        query_lower = query.lower()

        # Detect primary intent
        intent = self._detect_intent(query_lower)

        # Extract target data types
        target_data = self._extract_data_types(query_lower)

        # Extract symbols
        symbols = self._extract_symbols(query, context)
        primary_symbol = symbols[0] if symbols else None

        # Extract filters
        filters = self._extract_filters(query_lower, preferences)

        # Determine visualizations
        visualizations = self._determine_visualizations(query_lower, intent)

        # Determine interactions
        interactions = self._determine_interactions(query_lower, intent)

        # Extract time/expiration info
        time_range = self._extract_time_range(query_lower)
        expiration = self._extract_expiration(query_lower)

        # Check for educational intent
        educational = self._is_educational(query_lower)

        # Check for comparison
        comparison = self._is_comparison(query_lower)

        return RequirementSpec(
            intent=intent,
            target_data=target_data,
            symbol=primary_symbol,
            symbols=symbols if len(symbols) > 1 else None,
            filters=filters if filters else None,
            visualizations=visualizations,
            interactions=interactions,
            time_range=time_range,
            expiration=expiration,
            educational=educational,
            comparison=comparison,
        )

    def _detect_intent(self, query: str) -> str:
        """Detect the primary intent of the query."""
        scores = {}

        for intent, patterns in self._intent_compiled.items():
            score = sum(1 for p in patterns if p.search(query))
            if score > 0:
                scores[intent] = score

        if not scores:
            return "general_view"

        return max(scores, key=scores.get)

    def _extract_data_types(self, query: str) -> List[str]:
        """Extract required data types from query."""
        data_types = []

        for data_type, patterns in self._data_compiled.items():
            if any(p.search(query) for p in patterns):
                data_types.append(data_type)

        return data_types if data_types else ["quote"]

    def _extract_symbols(
        self,
        query: str,
        context: Optional[GenerationContext]
    ) -> List[str]:
        """Extract stock symbols from query and context."""
        symbols = []

        # Extract from query using pattern
        potential_symbols = self._symbol_pattern.findall(query)
        for sym in potential_symbols:
            # Handle case where findall returns tuple (from capture groups)
            if isinstance(sym, tuple):
                sym = sym[0]
            sym_upper = sym.upper()
            if sym_upper not in self._non_tickers and len(sym_upper) <= 5:
                # Basic validation - real implementation would check against
                # a symbol database
                symbols.append(sym_upper)

        # Add from context if no symbols found
        if not symbols and context:
            if context.symbol:
                symbols.append(context.symbol.upper())
            elif context.watchlist:
                symbols.extend([s.upper() for s in context.watchlist[:3]])

        return list(dict.fromkeys(symbols))  # Dedupe while preserving order

    def _extract_filters(
        self,
        query: str,
        preferences: Optional[UserPreferences]
    ) -> Dict[str, Any]:
        """Extract filter conditions from query."""
        filters = {}

        # OI filters
        if re.search(r'high\s+(?:open\s+interest|oi)', query):
            filters['oi_threshold'] = 'high'
        elif re.search(r'low\s+(?:open\s+interest|oi)', query):
            filters['oi_threshold'] = 'low'

        # Option type filters
        if re.search(r'\bcalls?\b', query) and not re.search(r'\bputs?\b', query):
            filters['option_type'] = 'calls'
        elif re.search(r'\bputs?\b', query) and not re.search(r'\bcalls?\b', query):
            filters['option_type'] = 'puts'

        # Strike filters
        if re.search(r'\batm\b|at.the.money', query):
            filters['strike_range'] = 'atm'
        elif re.search(r'\botm\b|out.of.the.money', query):
            filters['strike_range'] = 'otm'
        elif re.search(r'\bitm\b|in.the.money', query):
            filters['strike_range'] = 'itm'

        # IV filters
        if re.search(r'high\s+iv', query):
            filters['iv_threshold'] = 'high'
        elif re.search(r'low\s+iv', query):
            filters['iv_threshold'] = 'low'

        # Volume filters
        if re.search(r'high\s+volume', query):
            filters['volume_threshold'] = 'high'

        # Add expertise level from preferences
        if preferences:
            filters['expertise_level'] = preferences.expertise_level.value

        return filters

    def _determine_visualizations(self, query: str, intent: str) -> List[str]:
        """Determine required visualization types."""
        visualizations = []

        # Check explicit visualization mentions
        for viz, patterns in self._viz_compiled.items():
            if any(p.search(query) for p in patterns):
                visualizations.append(viz)

        # Add default visualizations based on intent
        if not visualizations:
            intent_viz_map = {
                "options_chain": ["table"],
                "greeks_display": ["gauge", "table"],
                "payoff_diagram": ["diagram", "chart"],
                "volatility_surface": ["3d"],
                "strategy_builder": ["diagram", "card"],
                "strategy_comparison": ["comparison", "diagram"],
                "portfolio_view": ["card", "table"],
                "educational": ["diagram", "card"],
                "earnings_calendar": ["timeline", "table"],
                "flow_analysis": ["table", "chart"],
                "alert_setup": ["card"],
                "gex_analysis": ["heatmap", "chart"],
                "quote_view": ["card"],
                "general_view": ["card"],
            }
            visualizations = intent_viz_map.get(intent, ["card"])

        return visualizations

    def _determine_interactions(self, query: str, intent: str) -> List[str]:
        """Determine required interactions."""
        interactions = []

        # Check explicit interaction mentions
        for inter, patterns in self._interaction_compiled.items():
            if any(p.search(query) for p in patterns):
                interactions.append(inter)

        # Add default interactions based on intent
        if not interactions:
            intent_interaction_map = {
                "options_chain": ["sort", "filter", "expand", "click"],
                "greeks_display": ["hover"],
                "payoff_diagram": ["hover", "zoom"],
                "volatility_surface": ["zoom", "drag"],
                "strategy_builder": ["drag", "click"],
                "strategy_comparison": ["toggle"],
                "portfolio_view": ["expand", "sort"],
                "educational": ["click", "expand"],
                "earnings_calendar": ["filter", "click"],
                "flow_analysis": ["sort", "filter"],
                "alert_setup": ["click", "toggle"],
                "gex_analysis": ["hover", "zoom"],
            }
            interactions = intent_interaction_map.get(intent, ["click"])

        return interactions

    def _extract_time_range(self, query: str) -> Optional[str]:
        """Extract time range from query."""
        patterns = [
            (r'(\d+)\s*days?', lambda m: f"{m.group(1)}d"),
            (r'(\d+)\s*weeks?', lambda m: f"{m.group(1)}w"),
            (r'(\d+)\s*months?', lambda m: f"{m.group(1)}m"),
            (r'(\d+)\s*years?', lambda m: f"{m.group(1)}y"),
            (r'today', lambda m: "1d"),
            (r'this\s+week', lambda m: "1w"),
            (r'this\s+month', lambda m: "1m"),
            (r'ytd', lambda m: "ytd"),
        ]

        for pattern, formatter in patterns:
            match = re.search(pattern, query)
            if match:
                return formatter(match)

        return None

    def _extract_expiration(self, query: str) -> Optional[str]:
        """Extract expiration date from query."""
        patterns = [
            # "Jan 19" or "January 19"
            r'(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|'
            r'jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|'
            r'dec(?:ember)?)\s+(\d{1,2})',
            # "Friday" or "next Friday"
            r'(?:this\s+|next\s+)?(friday|monday|weekly)',
            # "0DTE" or "0 DTE"
            r'(\d)\s*dte',
        ]

        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(0)

        return None

    def _is_educational(self, query: str) -> bool:
        """Check if query has educational intent."""
        educational_patterns = [
            r'explain',
            r'what\s+is',
            r'what\s+are',
            r'how\s+does',
            r'how\s+do',
            r'teach\s+me',
            r'learn',
            r'understand',
            r'tutorial',
            r'example',
            r'show\s+me\s+how',
        ]
        return any(re.search(p, query) for p in educational_patterns)

    def _is_comparison(self, query: str) -> bool:
        """Check if query involves comparison."""
        comparison_patterns = [
            r'\bvs\.?\b',
            r'versus',
            r'compare',
            r'which\s+is\s+better',
            r'difference\s+between',
            r'or\s+',
        ]
        return any(re.search(p, query) for p in comparison_patterns)


# Create singleton instance
requirement_parser = RequirementParser()
