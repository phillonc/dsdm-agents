"""Feasibility stage optimizations - fast-path, caching, and enhanced analysis."""

import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


# ==================== ASSESSMENT CACHE ====================

class FeasibilityCache:
    """Cache for common project type assessments to speed up feasibility evaluation."""

    def __init__(self, ttl_hours: int = 24):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = timedelta(hours=ttl_hours)
        self._hit_count = 0
        self._miss_count = 0

        # Pre-populate with common project type templates
        self._templates = {
            "web_app": {
                "technical_feasibility": True,
                "complexity": "medium",
                "common_stack": ["React", "Node.js", "PostgreSQL"],
                "common_risks": [
                    {"area": "security", "severity": "medium", "description": "Authentication/authorization implementation"},
                    {"area": "performance", "severity": "low", "description": "Frontend optimization needed"},
                    {"area": "integration", "severity": "low", "description": "API versioning considerations"},
                ],
                "dsdm_suitability": "high",
                "recommendation": "go",
            },
            "api_service": {
                "technical_feasibility": True,
                "complexity": "low",
                "common_stack": ["Python/FastAPI", "Node.js/Express", "Go"],
                "common_risks": [
                    {"area": "security", "severity": "medium", "description": "API security (rate limiting, auth)"},
                    {"area": "scalability", "severity": "medium", "description": "Load handling design"},
                ],
                "dsdm_suitability": "high",
                "recommendation": "go",
            },
            "mobile_app": {
                "technical_feasibility": True,
                "complexity": "medium",
                "common_stack": ["React Native", "Flutter", "Swift/Kotlin"],
                "common_risks": [
                    {"area": "platform", "severity": "medium", "description": "Cross-platform compatibility"},
                    {"area": "ux", "severity": "medium", "description": "Mobile UX patterns"},
                    {"area": "deployment", "severity": "low", "description": "App store approval process"},
                ],
                "dsdm_suitability": "high",
                "recommendation": "go",
            },
            "data_pipeline": {
                "technical_feasibility": True,
                "complexity": "medium",
                "common_stack": ["Python", "Apache Airflow", "Spark", "PostgreSQL/BigQuery"],
                "common_risks": [
                    {"area": "data_quality", "severity": "high", "description": "Data validation and quality checks"},
                    {"area": "performance", "severity": "medium", "description": "Large dataset handling"},
                    {"area": "reliability", "severity": "medium", "description": "Pipeline failure recovery"},
                ],
                "dsdm_suitability": "medium",
                "recommendation": "go",
            },
            "ml_project": {
                "technical_feasibility": True,
                "complexity": "high",
                "common_stack": ["Python", "TensorFlow/PyTorch", "MLflow", "Kubernetes"],
                "common_risks": [
                    {"area": "data", "severity": "high", "description": "Training data availability and quality"},
                    {"area": "model", "severity": "high", "description": "Model accuracy and bias"},
                    {"area": "infrastructure", "severity": "medium", "description": "GPU/compute resources"},
                    {"area": "maintenance", "severity": "medium", "description": "Model drift and retraining"},
                ],
                "dsdm_suitability": "medium",
                "recommendation": "go",
            },
            "cli_tool": {
                "technical_feasibility": True,
                "complexity": "low",
                "common_stack": ["Python", "Go", "Rust"],
                "common_risks": [
                    {"area": "usability", "severity": "low", "description": "Clear help/documentation"},
                    {"area": "compatibility", "severity": "low", "description": "Cross-platform support"},
                ],
                "dsdm_suitability": "high",
                "recommendation": "go",
            },
            "microservices": {
                "technical_feasibility": True,
                "complexity": "high",
                "common_stack": ["Docker", "Kubernetes", "API Gateway", "Message Queue"],
                "common_risks": [
                    {"area": "complexity", "severity": "high", "description": "Service orchestration and communication"},
                    {"area": "observability", "severity": "medium", "description": "Distributed tracing and monitoring"},
                    {"area": "data", "severity": "medium", "description": "Data consistency across services"},
                    {"area": "deployment", "severity": "medium", "description": "CI/CD pipeline complexity"},
                ],
                "dsdm_suitability": "medium",
                "recommendation": "go",
            },
        }

    def _generate_key(self, input_text: str) -> str:
        """Generate a cache key from input text."""
        # Normalize the input
        normalized = input_text.lower().strip()
        # Create a hash for the key
        return hashlib.md5(normalized.encode()).hexdigest()

    def get(self, input_text: str) -> Optional[Dict[str, Any]]:
        """Get cached assessment if available and not expired."""
        key = self._generate_key(input_text)

        if key in self._cache:
            entry = self._cache[key]
            if datetime.now() - entry["timestamp"] < self._ttl:
                self._hit_count += 1
                return entry["data"]
            else:
                # Expired, remove it
                del self._cache[key]

        self._miss_count += 1
        return None

    def set(self, input_text: str, assessment: Dict[str, Any]) -> None:
        """Cache an assessment result."""
        key = self._generate_key(input_text)
        self._cache[key] = {
            "timestamp": datetime.now(),
            "data": assessment,
        }

    def get_template(self, project_type: str) -> Optional[Dict[str, Any]]:
        """Get a pre-defined template for a project type."""
        return self._templates.get(project_type.lower().replace(" ", "_").replace("-", "_"))

    def detect_project_type(self, input_text: str) -> Optional[str]:
        """Detect project type from input text using keyword matching."""
        text_lower = input_text.lower()

        # Define keyword patterns for each project type
        patterns = {
            "web_app": ["web app", "website", "web application", "frontend", "dashboard", "portal", "spa", "single page"],
            "api_service": ["api", "rest api", "graphql", "backend service", "microservice api", "web service"],
            "mobile_app": ["mobile app", "ios app", "android app", "react native", "flutter", "mobile application"],
            "data_pipeline": ["data pipeline", "etl", "data processing", "data ingestion", "batch processing", "data warehouse"],
            "ml_project": ["machine learning", "ml model", "ai", "neural network", "deep learning", "prediction model", "nlp"],
            "cli_tool": ["cli", "command line", "terminal tool", "shell script", "command-line"],
            "microservices": ["microservices", "distributed system", "service mesh", "event-driven"],
        }

        # Score each type based on keyword matches
        scores = {}
        for project_type, keywords in patterns.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[project_type] = score

        if scores:
            return max(scores, key=scores.get)
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cache_size": len(self._cache),
            "hit_count": self._hit_count,
            "miss_count": self._miss_count,
            "hit_rate": self._hit_count / (self._hit_count + self._miss_count) if (self._hit_count + self._miss_count) > 0 else 0,
        }


# Global cache instance
_feasibility_cache = FeasibilityCache()


def get_feasibility_cache() -> FeasibilityCache:
    """Get the global feasibility cache instance."""
    return _feasibility_cache


# ==================== QUICK FEASIBILITY FAST-PATH ====================

class QuickFeasibilityResult:
    """Result of quick feasibility assessment."""

    def __init__(
        self,
        is_quick_path: bool,
        recommendation: str,  # "go", "no-go", "needs_analysis"
        confidence: float,  # 0.0 to 1.0
        reasons: List[str],
        project_type: Optional[str] = None,
        cached_assessment: Optional[Dict[str, Any]] = None,
    ):
        self.is_quick_path = is_quick_path
        self.recommendation = recommendation
        self.confidence = confidence
        self.reasons = reasons
        self.project_type = project_type
        self.cached_assessment = cached_assessment


def quick_feasibility_check(input_text: str) -> QuickFeasibilityResult:
    """
    Perform a quick feasibility check to determine if full analysis is needed.

    Returns a QuickFeasibilityResult indicating whether to fast-track or do full analysis.
    """
    cache = get_feasibility_cache()
    reasons = []

    # Check 1: Very short input (likely too vague)
    word_count = len(input_text.split())
    if word_count < 5:
        return QuickFeasibilityResult(
            is_quick_path=True,
            recommendation="needs_analysis",
            confidence=0.9,
            reasons=["Input too brief - need more details for feasibility assessment"],
        )

    # Check 2: Cached result exists
    cached = cache.get(input_text)
    if cached:
        reasons.append("Using cached feasibility assessment")
        return QuickFeasibilityResult(
            is_quick_path=True,
            recommendation=cached.get("recommendation", "go"),
            confidence=0.95,
            reasons=reasons,
            cached_assessment=cached,
        )

    # Check 3: Detect project type and use template
    project_type = cache.detect_project_type(input_text)
    if project_type:
        template = cache.get_template(project_type)
        if template:
            reasons.append(f"Detected standard project type: {project_type}")

            # Check for red flags that would override the template
            red_flags = _detect_red_flags(input_text)
            if red_flags:
                reasons.extend([f"Red flag: {rf}" for rf in red_flags])
                return QuickFeasibilityResult(
                    is_quick_path=False,
                    recommendation="needs_analysis",
                    confidence=0.5,
                    reasons=reasons,
                    project_type=project_type,
                )

            # Standard project type without red flags - fast track
            return QuickFeasibilityResult(
                is_quick_path=True,
                recommendation=template["recommendation"],
                confidence=0.85,
                reasons=reasons,
                project_type=project_type,
                cached_assessment=template,
            )

    # Check 4: Simple project indicators (positive signals)
    simple_indicators = _detect_simple_project(input_text)
    if simple_indicators["is_simple"]:
        reasons.extend(simple_indicators["reasons"])
        return QuickFeasibilityResult(
            is_quick_path=True,
            recommendation="go",
            confidence=0.8,
            reasons=reasons,
        )

    # Check 5: Known infeasible patterns
    infeasible = _detect_infeasible_patterns(input_text)
    if infeasible["is_infeasible"]:
        reasons.extend(infeasible["reasons"])
        return QuickFeasibilityResult(
            is_quick_path=True,
            recommendation="no-go",
            confidence=infeasible["confidence"],
            reasons=reasons,
        )

    # Default: needs full analysis
    return QuickFeasibilityResult(
        is_quick_path=False,
        recommendation="needs_analysis",
        confidence=0.5,
        reasons=["Project requires detailed feasibility analysis"],
        project_type=project_type,
    )


def _detect_red_flags(input_text: str) -> List[str]:
    """Detect red flags that require detailed analysis."""
    red_flags = []
    text_lower = input_text.lower()

    patterns = {
        "regulatory": ["hipaa", "gdpr", "pci", "sox", "compliance", "regulated"],
        "legacy_integration": ["legacy system", "mainframe", "cobol", "as400"],
        "real_time_critical": ["real-time trading", "life-critical", "safety-critical"],
        "massive_scale": ["billion users", "petabyte", "global scale", "million concurrent"],
        "novel_technology": ["quantum", "blockchain for everything", "revolutionary new"],
        "unclear_scope": ["everything", "complete solution for all", "solve all problems"],
    }

    for category, keywords in patterns.items():
        for kw in keywords:
            if kw in text_lower:
                red_flags.append(f"{category}: '{kw}' detected")
                break

    return red_flags


def _detect_simple_project(input_text: str) -> Dict[str, Any]:
    """Detect indicators of a simple, feasible project."""
    text_lower = input_text.lower()
    reasons = []
    score = 0

    # Simple scope indicators
    simple_patterns = [
        ("crud", "Standard CRUD operations"),
        ("basic", "Basic functionality requested"),
        ("simple", "Explicitly simple scope"),
        ("prototype", "Prototype/POC scope"),
        ("mvp", "MVP scope"),
        ("internal tool", "Internal tool (limited users)"),
        ("admin panel", "Admin panel (well-understood pattern)"),
    ]

    for pattern, reason in simple_patterns:
        if pattern in text_lower:
            score += 1
            reasons.append(reason)

    # Technology clarity indicators
    tech_patterns = [
        ("using react", "Clear frontend technology"),
        ("using python", "Clear backend technology"),
        ("postgresql", "Clear database choice"),
        ("mongodb", "Clear database choice"),
    ]

    for pattern, reason in tech_patterns:
        if pattern in text_lower:
            score += 0.5
            reasons.append(reason)

    return {
        "is_simple": score >= 2,
        "score": score,
        "reasons": reasons,
    }


def _detect_infeasible_patterns(input_text: str) -> Dict[str, Any]:
    """Detect patterns that indicate likely infeasibility."""
    text_lower = input_text.lower()
    reasons = []
    confidence = 0.0

    # Definitely infeasible
    definite_no_go = [
        ("hack into", "Security/ethical violation"),
        ("bypass security", "Security/ethical violation"),
        ("unlimited storage free", "Economically infeasible"),
        ("100% uptime guarantee", "Technically impossible"),
        ("never fail", "Technically impossible"),
    ]

    for pattern, reason in definite_no_go:
        if pattern in text_lower:
            reasons.append(reason)
            confidence = 0.95

    # Likely infeasible
    likely_no_go = [
        ("tomorrow deadline", "Unrealistic timeline"),
        ("no budget", "Resource constraints"),
        ("replace google", "Unrealistic scope"),
        ("better than chatgpt", "Unrealistic scope for typical project"),
    ]

    for pattern, reason in likely_no_go:
        if pattern in text_lower:
            reasons.append(reason)
            if confidence < 0.8:
                confidence = 0.8

    return {
        "is_infeasible": len(reasons) > 0,
        "confidence": confidence,
        "reasons": reasons,
    }


# ==================== ENHANCED ANALYSIS TOOLS ====================

def analyze_requirements_enhanced(requirements_text: str, focus_areas: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Enhanced requirements analysis that extracts structured information.

    This performs actual text analysis instead of just returning metadata.
    """
    # Extract sentences and key phrases
    sentences = [s.strip() for s in re.split(r'[.!?\n]', requirements_text) if s.strip()]

    # Categorize requirements
    functional_reqs = []
    non_functional_reqs = []
    constraints = []
    assumptions = []
    ambiguities = []

    # Keywords for categorization
    nfr_keywords = ["performance", "security", "scalability", "reliability", "availability",
                    "maintainability", "usability", "accessible", "fast", "secure", "scale"]
    constraint_keywords = ["must", "cannot", "required", "mandatory", "limit", "budget",
                          "deadline", "restriction", "compliance"]
    assumption_keywords = ["assume", "assuming", "expected", "will have", "should have"]

    for sentence in sentences:
        sentence_lower = sentence.lower()

        # Check for ambiguities
        if any(word in sentence_lower for word in ["maybe", "possibly", "might", "could be", "tbd", "unclear"]):
            ambiguities.append(sentence)
            continue

        # Categorize
        if any(kw in sentence_lower for kw in assumption_keywords):
            assumptions.append(sentence)
        elif any(kw in sentence_lower for kw in constraint_keywords):
            constraints.append(sentence)
        elif any(kw in sentence_lower for kw in nfr_keywords):
            non_functional_reqs.append(sentence)
        elif len(sentence) > 10:  # Meaningful sentence
            functional_reqs.append(sentence)

    # Extract entities (simple pattern matching)
    entities = {
        "users": _extract_user_types(requirements_text),
        "features": _extract_features(requirements_text),
        "technologies": _extract_technologies(requirements_text),
        "integrations": _extract_integrations(requirements_text),
    }

    # Determine focus areas automatically if not provided
    detected_focus = focus_areas or []
    if not detected_focus:
        if any("security" in s.lower() for s in sentences):
            detected_focus.append("security")
        if any("performance" in s.lower() for s in sentences):
            detected_focus.append("performance")
        if any("mobile" in s.lower() for s in sentences):
            detected_focus.append("mobile")
        if any("api" in s.lower() for s in sentences):
            detected_focus.append("api")
        if not detected_focus:
            detected_focus.append("general")

    return {
        "status": "analyzed",
        "summary": {
            "total_sentences": len(sentences),
            "functional_requirements": len(functional_reqs),
            "non_functional_requirements": len(non_functional_reqs),
            "constraints": len(constraints),
            "assumptions": len(assumptions),
            "ambiguities": len(ambiguities),
        },
        "functional_requirements": functional_reqs[:10],  # Top 10
        "non_functional_requirements": non_functional_reqs[:5],
        "constraints": constraints[:5],
        "assumptions": assumptions[:3],
        "ambiguities": ambiguities,
        "entities": entities,
        "focus_areas": detected_focus,
        "timestamp": datetime.now().isoformat(),
    }


def assess_technical_feasibility_enhanced(
    technology_stack: List[str],
    complexity_level: str = "medium",
    constraints: Optional[List[str]] = None,
    requirements_analysis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Enhanced technical feasibility assessment with real analysis.
    """
    # Technology maturity assessment
    mature_technologies = {
        "react", "vue", "angular", "python", "java", "javascript", "typescript",
        "node.js", "postgresql", "mysql", "mongodb", "redis", "docker", "kubernetes",
        "aws", "gcp", "azure", "fastapi", "django", "flask", "spring", "express",
    }

    experimental_technologies = {
        "quantum", "web3", "blockchain", "nft", "metaverse",
    }

    stack_lower = [t.lower() for t in technology_stack]
    mature_count = sum(1 for t in stack_lower if any(m in t for m in mature_technologies))
    experimental_count = sum(1 for t in stack_lower if any(e in t for e in experimental_technologies))

    # Calculate feasibility score
    base_score = 0.8

    # Adjust for technology maturity
    if mature_count >= len(stack_lower) * 0.7:
        base_score += 0.1
    if experimental_count > 0:
        base_score -= 0.2 * experimental_count

    # Adjust for complexity
    complexity_adjustments = {"low": 0.1, "medium": 0, "high": -0.1}
    base_score += complexity_adjustments.get(complexity_level, 0)

    # Assess constraints impact
    constraint_risks = []
    if constraints:
        for constraint in constraints:
            constraint_lower = constraint.lower()
            if "tight deadline" in constraint_lower or "asap" in constraint_lower:
                constraint_risks.append({"constraint": constraint, "impact": "high", "risk": "Schedule risk"})
                base_score -= 0.1
            elif "limited budget" in constraint_lower:
                constraint_risks.append({"constraint": constraint, "impact": "medium", "risk": "Resource risk"})
                base_score -= 0.05
            elif "legacy" in constraint_lower:
                constraint_risks.append({"constraint": constraint, "impact": "medium", "risk": "Integration risk"})
                base_score -= 0.05

    # Determine recommendation
    feasibility_score = max(0, min(1, base_score))

    if feasibility_score >= 0.7:
        recommendation = "Proceed"
        feasible = True
    elif feasibility_score >= 0.5:
        recommendation = "Proceed with caution"
        feasible = True
    else:
        recommendation = "Requires further assessment"
        feasible = False

    # Generate specific recommendations
    recommendations = []
    if experimental_count > 0:
        recommendations.append("Consider using more mature technology alternatives")
    if complexity_level == "high":
        recommendations.append("Break down into smaller, manageable components")
    if constraint_risks:
        recommendations.append("Address identified constraint risks early")

    return {
        "feasible": feasible,
        "feasibility_score": round(feasibility_score, 2),
        "technology_stack": technology_stack,
        "technology_assessment": {
            "mature_technologies": mature_count,
            "experimental_technologies": experimental_count,
            "coverage": f"{mature_count}/{len(stack_lower)} mature",
        },
        "complexity": complexity_level,
        "constraints": constraints or [],
        "constraint_risks": constraint_risks,
        "recommendation": recommendation,
        "recommendations": recommendations,
        "timestamp": datetime.now().isoformat(),
    }


def identify_risks_enhanced(
    risk_areas: List[str],
    severity_threshold: str = "medium",
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Enhanced risk identification with detailed risk analysis.
    """
    severity_levels = {"low": 1, "medium": 2, "high": 3}
    threshold_value = severity_levels.get(severity_threshold, 2)

    # Risk templates by area
    risk_templates = {
        "technical": [
            {"description": "Technology stack complexity", "probability": "medium", "impact": "medium", "mitigation": "Use proven technologies and patterns"},
            {"description": "Integration challenges", "probability": "medium", "impact": "high", "mitigation": "Early integration testing and API contracts"},
            {"description": "Performance bottlenecks", "probability": "low", "impact": "high", "mitigation": "Performance testing and optimization sprints"},
        ],
        "security": [
            {"description": "Data breach vulnerability", "probability": "low", "impact": "high", "mitigation": "Security audit and penetration testing"},
            {"description": "Authentication weaknesses", "probability": "medium", "impact": "high", "mitigation": "Use established auth providers (OAuth, etc.)"},
            {"description": "API security gaps", "probability": "medium", "impact": "medium", "mitigation": "API gateway, rate limiting, input validation"},
        ],
        "schedule": [
            {"description": "Scope creep", "probability": "high", "impact": "medium", "mitigation": "Strict change control and MoSCoW prioritization"},
            {"description": "Resource availability", "probability": "medium", "impact": "medium", "mitigation": "Resource planning and backup allocation"},
            {"description": "Dependency delays", "probability": "medium", "impact": "high", "mitigation": "Identify dependencies early, parallel workstreams"},
        ],
        "business": [
            {"description": "Requirements ambiguity", "probability": "medium", "impact": "high", "mitigation": "Regular stakeholder reviews and prototyping"},
            {"description": "Stakeholder alignment", "probability": "low", "impact": "high", "mitigation": "Regular demos and communication"},
            {"description": "Market timing", "probability": "low", "impact": "medium", "mitigation": "MVP approach with iterative releases"},
        ],
        "data": [
            {"description": "Data quality issues", "probability": "medium", "impact": "high", "mitigation": "Data validation and cleansing pipelines"},
            {"description": "Data migration complexity", "probability": "medium", "impact": "medium", "mitigation": "Phased migration with rollback plans"},
            {"description": "Privacy compliance", "probability": "low", "impact": "high", "mitigation": "Privacy-by-design and legal review"},
        ],
        "infrastructure": [
            {"description": "Scalability limitations", "probability": "low", "impact": "high", "mitigation": "Cloud-native architecture and auto-scaling"},
            {"description": "Deployment complexity", "probability": "medium", "impact": "medium", "mitigation": "CI/CD pipeline and infrastructure-as-code"},
            {"description": "Monitoring gaps", "probability": "medium", "impact": "medium", "mitigation": "Observability stack implementation"},
        ],
    }

    identified_risks = []
    risk_id = 1

    for area in risk_areas:
        area_lower = area.lower()

        # Find matching risk templates
        matched_area = None
        for template_area in risk_templates:
            if template_area in area_lower or area_lower in template_area:
                matched_area = template_area
                break

        if matched_area:
            for risk in risk_templates[matched_area]:
                risk_severity = severity_levels.get(risk["impact"], 2)
                if risk_severity >= threshold_value:
                    identified_risks.append({
                        "id": f"RISK-{risk_id:03d}",
                        "area": area,
                        "category": matched_area,
                        **risk,
                    })
                    risk_id += 1
        else:
            # Generic risk for unknown area
            identified_risks.append({
                "id": f"RISK-{risk_id:03d}",
                "area": area,
                "category": "general",
                "description": f"Potential risks in {area} area",
                "probability": "medium",
                "impact": "medium",
                "mitigation": f"Detailed {area} assessment required",
            })
            risk_id += 1

    # Calculate risk summary
    high_risks = sum(1 for r in identified_risks if r["impact"] == "high")
    medium_risks = sum(1 for r in identified_risks if r["impact"] == "medium")
    low_risks = sum(1 for r in identified_risks if r["impact"] == "low")

    # Overall risk level
    if high_risks >= 3:
        overall_risk = "high"
    elif high_risks >= 1 or medium_risks >= 3:
        overall_risk = "medium"
    else:
        overall_risk = "low"

    return {
        "risks_identified": len(identified_risks),
        "risk_areas_analyzed": risk_areas,
        "severity_threshold": severity_threshold,
        "risks": identified_risks,
        "summary": {
            "high_impact": high_risks,
            "medium_impact": medium_risks,
            "low_impact": low_risks,
            "overall_risk_level": overall_risk,
        },
        "top_mitigations": [r["mitigation"] for r in identified_risks[:5]],
        "status": "documented",
        "timestamp": datetime.now().isoformat(),
    }


# ==================== HELPER FUNCTIONS ====================

def _extract_user_types(text: str) -> List[str]:
    """Extract user types from requirements text."""
    user_patterns = [
        r"(admin|administrator)s?",
        r"(user|customer|client)s?",
        r"(manager|supervisor)s?",
        r"(developer|engineer)s?",
        r"(analyst|reviewer)s?",
        r"(guest|visitor)s?",
    ]

    users = set()
    text_lower = text.lower()
    for pattern in user_patterns:
        matches = re.findall(pattern, text_lower)
        users.update(matches)

    return list(users)[:5]


def _extract_features(text: str) -> List[str]:
    """Extract feature keywords from requirements text."""
    feature_patterns = [
        r"(login|authentication|auth)",
        r"(dashboard|admin panel)",
        r"(search|filter)",
        r"(notification|alert)s?",
        r"(report|analytics)",
        r"(upload|download)",
        r"(payment|checkout)",
        r"(profile|account)",
        r"(messaging|chat)",
        r"(export|import)",
    ]

    features = set()
    text_lower = text.lower()
    for pattern in feature_patterns:
        if re.search(pattern, text_lower):
            features.add(re.search(pattern, text_lower).group(1))

    return list(features)[:10]


def _extract_technologies(text: str) -> List[str]:
    """Extract technology mentions from requirements text."""
    tech_keywords = [
        "react", "vue", "angular", "python", "java", "javascript", "typescript",
        "node", "postgresql", "mysql", "mongodb", "redis", "docker", "kubernetes",
        "aws", "gcp", "azure", "fastapi", "django", "flask", "spring", "express",
        "graphql", "rest", "grpc", "kafka", "rabbitmq", "elasticsearch",
    ]

    found = []
    text_lower = text.lower()
    for tech in tech_keywords:
        if tech in text_lower:
            found.append(tech)

    return found


def _extract_integrations(text: str) -> List[str]:
    """Extract integration mentions from requirements text."""
    integration_patterns = [
        r"integrate with (\w+)",
        r"(\w+) integration",
        r"connect to (\w+)",
        r"sync with (\w+)",
        r"(\w+) api",
    ]

    integrations = set()
    text_lower = text.lower()
    for pattern in integration_patterns:
        matches = re.findall(pattern, text_lower)
        integrations.update(matches)

    # Filter common words
    common_words = {"the", "a", "an", "this", "that", "our", "their", "rest", "web"}
    integrations = [i for i in integrations if i not in common_words]

    return list(integrations)[:5]


def generate_quick_feasibility_report(result: QuickFeasibilityResult, input_text: str) -> str:
    """Generate a formatted feasibility report from quick assessment."""
    report = f"""# Quick Feasibility Assessment

## Recommendation: **{result.recommendation.upper()}**

**Confidence Level:** {result.confidence * 100:.0f}%
**Assessment Type:** {'Fast-tracked' if result.is_quick_path else 'Full analysis required'}
"""

    if result.project_type:
        report += f"**Detected Project Type:** {result.project_type.replace('_', ' ').title()}\n"

    report += "\n## Assessment Reasons\n"
    for reason in result.reasons:
        report += f"- {reason}\n"

    if result.cached_assessment:
        assessment = result.cached_assessment
        report += f"""
## Technical Assessment

**Complexity:** {assessment.get('complexity', 'N/A')}
**DSDM Suitability:** {assessment.get('dsdm_suitability', 'N/A')}

### Suggested Technology Stack
"""
        for tech in assessment.get('common_stack', []):
            report += f"- {tech}\n"

        report += "\n### Identified Risks\n"
        for risk in assessment.get('common_risks', []):
            report += f"- **{risk['area'].title()}** ({risk['severity']}): {risk['description']}\n"

    report += f"""
## Next Steps

"""
    if result.recommendation == "go":
        report += """1. Proceed to Business Study phase
2. Validate assumptions with stakeholders
3. Begin detailed requirements gathering
"""
    elif result.recommendation == "no-go":
        report += """1. Review identified blockers
2. Discuss constraints with stakeholders
3. Consider alternative approaches or scope reduction
"""
    else:
        report += """1. Conduct detailed feasibility analysis
2. Gather more requirements information
3. Assess technical and business constraints
"""

    return report
