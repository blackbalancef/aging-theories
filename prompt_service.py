from pathlib import Path
from jinja2 import Environment, FileSystemLoader, Template
from loguru import logger
from prompt_schemas import BasePromptSchema


class PromptService:
    """Service for loading and compiling Jinja2 prompt templates"""
    
    def __init__(self, prompts_dir: str | Path = "prompts"):
        """
        Initialize the PromptService
        
        Args:
            prompts_dir: Directory containing the prompt templates
        """
        self.prompts_dir = Path(prompts_dir)
        if not self.prompts_dir.exists():
            raise ValueError(f"Prompts directory does not exist: {self.prompts_dir}")
        
        # Set up Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.prompts_dir)),
            autoescape=False,  # We don't need HTML escaping for prompts
            trim_blocks=True,
            lstrip_blocks=True
        )
        logger.info(f"PromptService initialized with prompts directory: {self.prompts_dir}")
    
    def compile_prompt(self, prompt_schema: BasePromptSchema) -> str:
        """
        Load a prompt template and compile it with data from the schema
        
        Args:
            prompt_schema: Instance of a prompt schema containing the template name and data
            
        Returns:
            Compiled prompt string
            
        Raises:
            FileNotFoundError: If the template file doesn't exist
            ValueError: If template compilation fails
        """
        # Extract the filename from the schema
        filename = prompt_schema.filename
        
        # Ensure the filename has .j2 extension
        if not filename.endswith('.j2'):
            filename = f"{filename}.j2"
        
        logger.debug(f"Loading template: {filename}")
        
        try:
            # Load the template
            template = self.env.get_template(filename)
            
            # Convert the schema to dict, excluding the filename field
            template_data = prompt_schema.model_dump(exclude={'filename'})
            
            logger.debug(f"Compiling template with data: {template_data}")
            
            # Render the template with the data
            compiled_prompt = template.render(**template_data)
            
            logger.info(f"Successfully compiled prompt from template: {filename}")
            return compiled_prompt
            
        except Exception as e:
            logger.error(f"Failed to compile prompt from template {filename}: {e}")
            raise
    
    def get_template_names(self) -> list[str]:
        """
        Get list of all available template names
        
        Returns:
            List of template filenames
        """
        return [f.name for f in self.prompts_dir.glob("*.j2")]

