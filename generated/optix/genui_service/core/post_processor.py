"""
Post-Processing Pipeline

Pipeline of post-processors to sanitize and validate generated UI code.
Addresses common generation issues and ensures security compliance.
"""

import re
import html
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class ProcessingResult:
    """Result from a processor."""
    html: str
    modified: bool = False
    warnings: List[str] = None
    errors: List[str] = None

    def __post_init__(self):
        self.warnings = self.warnings or []
        self.errors = self.errors or []


@dataclass
class ProcessedUI:
    """Final processed UI output."""
    html: str
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    modifications: List[str]


class BaseProcessor(ABC):
    """Base class for post-processors."""

    @abstractmethod
    async def process(
        self,
        html_content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ProcessingResult:
        """Process the HTML content."""
        pass


class SecuritySanitizer(BaseProcessor):
    """
    Ensures generated code is safe for sandboxed execution.
    Removes dangerous patterns and injects CSP headers.
    """

    BLOCKED_PATTERNS = [
        (r'eval\s*\(', '/* BLOCKED: eval */'),
        (r'Function\s*\(', '/* BLOCKED: Function */'),
        (r'document\.write', '/* BLOCKED: document.write */'),
        (r'innerHTML\s*=', 'textContent ='),  # Replace with safer alternative
        (r'window\.location\s*=', '/* BLOCKED: window.location */'),
        (r'document\.cookie', '/* BLOCKED: document.cookie */'),
        (r'localStorage\.', '/* BLOCKED: localStorage */'),
        (r'sessionStorage\.', '/* BLOCKED: sessionStorage */'),
        (r'fetch\s*\(', 'dataBridge.request('),  # Redirect to bridged API
        (r'XMLHttpRequest', '/* BLOCKED: XMLHttpRequest */'),
        (r'<script\s+src=', '<!-- BLOCKED: external script -->'),
        (r'<iframe', '<!-- BLOCKED: iframe -->'),
        (r'javascript:', '/* BLOCKED: javascript: */'),
        (r'data:text/html', '/* BLOCKED: data:text/html */'),
    ]

    REQUIRED_CSP = {
        "default-src": "'self'",
        "script-src": "'self' 'unsafe-inline'",
        "style-src": "'self' 'unsafe-inline'",
        "img-src": "'self' data: https:",
        "connect-src": "'self'",
        "font-src": "'self' https:",
        "frame-ancestors": "'none'",
    }

    async def process(
        self,
        html_content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ProcessingResult:
        """Sanitize HTML for security."""
        result_html = html_content
        warnings = []
        modified = False

        # Check and replace blocked patterns
        for pattern, replacement in self.BLOCKED_PATTERNS:
            if re.search(pattern, result_html, re.IGNORECASE):
                result_html = re.sub(
                    pattern,
                    replacement,
                    result_html,
                    flags=re.IGNORECASE
                )
                warnings.append(f"Blocked pattern: {pattern}")
                modified = True

        # Remove inline event handlers (onclick, onerror, etc.)
        inline_handlers = re.findall(r'\bon\w+\s*=\s*["\'][^"\']*["\']', result_html)
        for handler in inline_handlers:
            result_html = result_html.replace(handler, '')
            warnings.append(f"Removed inline handler: {handler[:30]}...")
            modified = True

        # Inject CSP meta tag if not present
        csp_content = "; ".join(
            f"{k} {v}" for k, v in self.REQUIRED_CSP.items()
        )
        csp_tag = f'<meta http-equiv="Content-Security-Policy" content="{csp_content}">'

        if "Content-Security-Policy" not in result_html:
            if "<head>" in result_html:
                result_html = result_html.replace(
                    "<head>",
                    f"<head>\n  {csp_tag}"
                )
                modified = True
            elif "<html>" in result_html:
                result_html = result_html.replace(
                    "<html>",
                    f"<html>\n<head>\n  {csp_tag}\n</head>"
                )
                modified = True

        return ProcessingResult(
            html=result_html,
            modified=modified,
            warnings=warnings,
        )


class StyleNormalizer(BaseProcessor):
    """Ensures consistent styling with OPTIX design system."""

    DESIGN_TOKENS = """
    :root {
      /* Colors */
      --optix-primary: #2563EB;
      --optix-primary-hover: #1D4ED8;
      --optix-bg-dark: #0F172A;
      --optix-bg-light: #1E293B;
      --optix-bg-card: #1E293B;
      --optix-text: #F1F5F9;
      --optix-text-muted: #94A3B8;
      --optix-green: #22C55E;
      --optix-red: #EF4444;
      --optix-yellow: #EAB308;
      --optix-border: #334155;

      /* Typography */
      --optix-font: Inter, system-ui, -apple-system, sans-serif;
      --optix-font-mono: 'SF Mono', Consolas, monospace;

      /* Spacing */
      --optix-space-xs: 4px;
      --optix-space-sm: 8px;
      --optix-space-md: 16px;
      --optix-space-lg: 24px;
      --optix-space-xl: 32px;

      /* Border Radius */
      --optix-radius-sm: 4px;
      --optix-radius-md: 8px;
      --optix-radius-lg: 12px;

      /* Shadows */
      --optix-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    /* Dark mode defaults */
    body {
      font-family: var(--optix-font);
      background: var(--optix-bg-dark);
      color: var(--optix-text);
      margin: 0;
      padding: var(--optix-space-md);
      line-height: 1.5;
    }

    @media (prefers-color-scheme: light) {
      :root {
        --optix-bg-dark: #FFFFFF;
        --optix-bg-light: #F8FAFC;
        --optix-bg-card: #FFFFFF;
        --optix-text: #0F172A;
        --optix-text-muted: #64748B;
        --optix-border: #E2E8F0;
      }
    }
    """

    async def process(
        self,
        html_content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ProcessingResult:
        """Normalize styles."""
        result_html = html_content
        modified = False

        # Check if design tokens are already present
        if "--optix-primary" not in result_html:
            # Inject design tokens into <style> or create new <style> block
            if "<style>" in result_html:
                result_html = result_html.replace(
                    "<style>",
                    f"<style>\n{self.DESIGN_TOKENS}\n"
                )
                modified = True
            elif "</head>" in result_html:
                result_html = result_html.replace(
                    "</head>",
                    f"<style>\n{self.DESIGN_TOKENS}\n</style>\n</head>"
                )
                modified = True

        return ProcessingResult(
            html=result_html,
            modified=modified,
        )


class AccessibilityChecker(BaseProcessor):
    """Adds ARIA labels, roles, and checks accessibility."""

    async def process(
        self,
        html_content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ProcessingResult:
        """Check and enhance accessibility."""
        result_html = html_content
        warnings = []
        modified = False

        # Add lang attribute to html tag
        if '<html>' in result_html and 'lang=' not in result_html:
            result_html = result_html.replace('<html>', '<html lang="en">')
            modified = True

        # Check for images without alt text
        img_without_alt = re.findall(r'<img(?![^>]*alt=)[^>]*>', result_html)
        for img in img_without_alt:
            warnings.append(f"Image without alt text: {img[:50]}...")

        # Add role="main" to main content
        if '<main' in result_html and 'role=' not in result_html:
            result_html = result_html.replace('<main', '<main role="main"')
            modified = True

        # Check for buttons without accessible names
        button_without_text = re.findall(
            r'<button[^>]*>\s*<(?:img|svg|i)[^>]*>\s*</button>',
            result_html
        )
        for btn in button_without_text:
            warnings.append(f"Button without accessible name: {btn[:50]}...")

        # Add skip navigation link
        if '<body>' in result_html and 'skip-to-content' not in result_html:
            skip_link = '''<a href="#main-content" class="skip-link" style="
        position: absolute;
        top: -40px;
        left: 0;
        background: var(--optix-primary);
        color: white;
        padding: 8px;
        z-index: 100;
      ">Skip to main content</a>'''
            result_html = result_html.replace(
                '<body>',
                f'<body>\n  {skip_link}'
            )
            modified = True

        return ProcessingResult(
            html=result_html,
            modified=modified,
            warnings=warnings,
        )


class DataBindingResolver(BaseProcessor):
    """Resolves data placeholders in the generated UI."""

    async def process(
        self,
        html_content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ProcessingResult:
        """Resolve data bindings."""
        result_html = html_content
        modified = False

        # Find data placeholders {{DATA:endpoint:params}}
        placeholders = re.findall(r'\{\{DATA:([^}]+)\}\}', result_html)

        for placeholder in placeholders:
            parts = placeholder.split(':')
            endpoint = parts[0] if parts else 'unknown'

            # Replace with JavaScript data bridge call
            replacement = f'<span data-bind="{endpoint}" data-params="{":".join(parts[1:])}">[Loading...]</span>'
            result_html = result_html.replace(
                f'{{{{DATA:{placeholder}}}}}',
                replacement
            )
            modified = True

        # Add data bridge initialization script if bindings exist
        if 'data-bind=' in result_html and 'initDataBindings' not in result_html:
            binding_script = '''
<script>
  // Data bridge initialization
  (function() {
    const dataBridge = window.OPTIXDataBridge || {
      request: async (endpoint, params) => ({ loading: true }),
      subscribe: (channel, callback) => {}
    };

    async function initDataBindings() {
      const bindings = document.querySelectorAll('[data-bind]');
      for (const el of bindings) {
        const endpoint = el.dataset.bind;
        const params = el.dataset.params || '';
        try {
          const data = await dataBridge.request(endpoint, params);
          el.textContent = JSON.stringify(data);
          el.classList.remove('loading');
        } catch (e) {
          el.textContent = '[Error loading data]';
          el.classList.add('error');
        }
      }
    }

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', initDataBindings);
    } else {
      initDataBindings();
    }
  })();
</script>'''
            if '</body>' in result_html:
                result_html = result_html.replace(
                    '</body>',
                    f'{binding_script}\n</body>'
                )
                modified = True

        return ProcessingResult(
            html=result_html,
            modified=modified,
        )


class ErrorBoundaryInjector(BaseProcessor):
    """Wraps components in error handling."""

    ERROR_BOUNDARY_SCRIPT = '''
<script>
  // Global error handler
  window.onerror = function(msg, url, lineNo, columnNo, error) {
    const errorContainer = document.getElementById('error-boundary');
    if (errorContainer) {
      errorContainer.innerHTML = `
        <div style="
          padding: 16px;
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid var(--optix-red);
          border-radius: 8px;
          margin: 16px 0;
        ">
          <strong style="color: var(--optix-red);">Something went wrong</strong>
          <p style="color: var(--optix-text-muted); margin: 8px 0 0;">
            ${msg}
          </p>
          <button onclick="location.reload()" style="
            margin-top: 12px;
            padding: 8px 16px;
            background: var(--optix-primary);
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
          ">Reload</button>
        </div>
      `;
      errorContainer.style.display = 'block';
    }
    return false;
  };

  // Promise rejection handler
  window.onunhandledrejection = function(event) {
    console.error('Unhandled promise rejection:', event.reason);
  };
</script>'''

    async def process(
        self,
        html_content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ProcessingResult:
        """Inject error boundaries."""
        result_html = html_content
        modified = False

        # Add error boundary container if not present
        if 'id="error-boundary"' not in result_html:
            if '<body>' in result_html:
                result_html = result_html.replace(
                    '<body>',
                    '<body>\n  <div id="error-boundary" style="display:none;"></div>'
                )
                modified = True

        # Add error handling script
        if 'window.onerror' not in result_html:
            if '</body>' in result_html:
                result_html = result_html.replace(
                    '</body>',
                    f'{self.ERROR_BOUNDARY_SCRIPT}\n</body>'
                )
                modified = True

        return ProcessingResult(
            html=result_html,
            modified=modified,
        )


class MobileResponsiveness(BaseProcessor):
    """Ensures responsive layout for mobile devices."""

    RESPONSIVE_META = '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">'

    RESPONSIVE_STYLES = '''
    /* Mobile responsiveness */
    * {
      box-sizing: border-box;
    }

    @media (max-width: 768px) {
      body {
        padding: var(--optix-space-sm);
      }

      table {
        display: block;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
      }

      .card {
        margin-bottom: var(--optix-space-sm);
      }
    }

    /* Touch-friendly targets */
    button, a, [role="button"] {
      min-height: 44px;
      min-width: 44px;
    }

    /* Prevent text size adjustment */
    html {
      -webkit-text-size-adjust: 100%;
    }
    '''

    async def process(
        self,
        html_content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ProcessingResult:
        """Ensure mobile responsiveness."""
        result_html = html_content
        modified = False

        # Add viewport meta tag
        if 'viewport' not in result_html:
            if '<head>' in result_html:
                result_html = result_html.replace(
                    '<head>',
                    f'<head>\n  {self.RESPONSIVE_META}'
                )
                modified = True

        # Add responsive styles
        if '@media' not in result_html or 'max-width: 768px' not in result_html:
            if '</style>' in result_html:
                # Find the last </style> tag and add before it
                last_style = result_html.rfind('</style>')
                result_html = (
                    result_html[:last_style] +
                    f'\n{self.RESPONSIVE_STYLES}\n' +
                    result_html[last_style:]
                )
                modified = True

        return ProcessingResult(
            html=result_html,
            modified=modified,
        )


class PostProcessor:
    """
    Main post-processing pipeline.
    Runs all processors in sequence on generated UI code.
    """

    def __init__(self):
        """Initialize the post-processor with all processors."""
        self.processors: List[BaseProcessor] = [
            SecuritySanitizer(),
            StyleNormalizer(),
            AccessibilityChecker(),
            DataBindingResolver(),
            ErrorBoundaryInjector(),
            MobileResponsiveness(),
        ]

    async def process(
        self,
        generated_html: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ProcessedUI:
        """
        Run the full post-processing pipeline.

        Args:
            generated_html: Raw generated HTML
            context: Optional context for processing

        Returns:
            ProcessedUI with sanitized, validated HTML
        """
        result = generated_html
        all_errors = []
        all_warnings = []
        modifications = []

        for processor in self.processors:
            try:
                processor_result = await processor.process(result, context)
                result = processor_result.html

                if processor_result.modified:
                    modifications.append(processor.__class__.__name__)

                all_warnings.extend(processor_result.warnings or [])
                all_errors.extend(processor_result.errors or [])

            except Exception as e:
                all_errors.append(
                    f"{processor.__class__.__name__} error: {str(e)}"
                )

        return ProcessedUI(
            html=result,
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings,
            modifications=modifications,
        )


# Create singleton instance
post_processor = PostProcessor()
