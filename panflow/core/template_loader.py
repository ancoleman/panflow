"""
Template loader for the reporting module.

This module provides utilities for loading and rendering HTML templates
for the various report formats.
"""

import os
import json
from typing import Dict, Any, Optional, List, Union
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Import logging utilities
from ..core.logging_utils import logger, log, log_structured

class TemplateLoader:
    """
    Loads and renders HTML templates for report generation.
    
    This class provides methods for loading and rendering Jinja2 templates
    for the various report formats.
    """
    
    def __init__(self, template_dir: Optional[str] = None, custom_templates_dir: Optional[str] = None):
        """
        Initialize the template loader.
        
        Args:
            template_dir: Directory containing the templates. If None, uses the default 
                          templates directory in the panflow package.
            custom_templates_dir: Directory containing custom templates that will override 
                                  default templates. If None, only default templates are used.
        """
        if template_dir is None:
            # Use default templates directory in the package
            package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            template_dir = os.path.join(package_dir, 'templates')
        
        self.template_dir = template_dir
        self.custom_templates_dir = custom_templates_dir
        
        # Initialize Jinja2 environment
        if custom_templates_dir and os.path.exists(custom_templates_dir):
            # Use a chain loader to first check custom templates, then fall back to default
            from jinja2 import ChoiceLoader
            self.env = Environment(
                loader=ChoiceLoader([
                    FileSystemLoader(custom_templates_dir),
                    FileSystemLoader(template_dir)
                ]),
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True
            )
            logger.debug(f"Using custom templates from {custom_templates_dir} with fallback to {template_dir}")
        else:
            self.env = Environment(
                loader=FileSystemLoader(template_dir),
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True
            )
            logger.debug(f"Using default templates from {template_dir}")
        
        # Add JSON encoder filter
        self.env.filters['json_encode'] = lambda obj, indent=None: json.dumps(obj, indent=indent)
        
        # Add custom filters for formatting
        self.env.filters['format_date'] = lambda d: d.strftime('%Y-%m-%d %H:%M:%S') if hasattr(d, 'strftime') else str(d)
        self.env.filters['format_number'] = lambda n: f"{n:,}" if isinstance(n, (int, float)) else str(n)
        
        logger.debug(f"Initialized TemplateLoader with template directory: {template_dir}")
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a template with the given context.
        
        Args:
            template_name: Name of the template to render (relative to the template directory)
            context: Dictionary of context variables for the template
            
        Returns:
            Rendered template as a string
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            log_structured(
                "Error rendering template",
                "error",
                template_name=template_name,
                error_type=type(e).__name__,
                error_message=str(e),
                template_dir=self.template_dir,
                custom_templates_dir=getattr(self, 'custom_templates_dir', None)
            )
            # Fallback to a simple template with error message
            return f"""<!DOCTYPE html>
<html>
<head><title>Error Rendering Report</title></head>
<body>
    <h1>Error Rendering Report</h1>
    <p>An error occurred while rendering the template '{template_name}':</p>
    <pre>{str(e)}</pre>
</body>
</html>"""
    
    def render_security_policy_analysis(self, analysis: Dict[str, Any], include_hit_counts: bool = False) -> str:
        """
        Render the security policy analysis report.
        
        Args:
            analysis: Analysis data
            include_hit_counts: Whether hit count data is included
            
        Returns:
            Rendered HTML report as a string
        """
        context = {
            'analysis': analysis,
            'include_hit_counts': include_hit_counts
        }
        return self.render_template('reports/security_policy_analysis.html', context)
    
    def render_object_usage_report(self, analysis: Dict[str, Any]) -> str:
        """
        Render the object usage report.
        
        Args:
            analysis: Analysis data
            
        Returns:
            Rendered HTML report as a string
        """
        context = {
            'analysis': analysis
        }
        return self.render_template('reports/object_usage.html', context)
    
    def render_custom_report(self, report: Dict[str, Any]) -> str:
        """
        Render a custom report.
        
        Args:
            report: Report data
            
        Returns:
            Rendered HTML report as a string
        """
        context = {
            'report': report
        }
        return self.render_template('reports/custom_report.html', context)
    
    def list_available_templates(self) -> List[str]:
        """
        List all available report templates.
        
        Returns:
            List of template names
        """
        try:
            templates_path = os.path.join(self.template_dir, 'reports')
            if not os.path.exists(templates_path):
                return []
            
            templates = []
            for filename in os.listdir(templates_path):
                if filename.endswith('.html') and not filename.startswith('_'):
                    templates.append(filename)
            
            return templates
        except Exception as e:
            logger.error(f"Error listing templates: {e}")
            return []
    
    def get_template_path(self, template_name: str) -> str:
        """
        Get the full path for a template.
        
        Args:
            template_name: Name of the template (relative to the template directory)
            
        Returns:
            Full path to the template
        """
        return os.path.join(self.template_dir, template_name)