"""
Conversation Analyzer
Analyzes conversation flow, extracts information, and determines outcomes
"""
import re
import logging
from typing import List, Dict, Any, Set
from pathlib import Path
from .models import ConversationSummary, ConversationOutcome, InformationGathered, ConversationTurn

logger = logging.getLogger(__name__)

class ConversationAnalyzer:
    """Analyzes conversations and extracts structured information"""
    
    def __init__(self):
        self.summary_phrases = [
            "here's the role", "here is the role", "to summarize", "summary of the role",
            "candidate preview", "publish", "job description", "role summary",
            "should i lock these in", "great, i've got everything"
        ]
        self.mandatory_fields = self._load_mandatory_fields()
        
        self.confirmation_phrases = [
            "yes", "looks good", "that's correct", "perfect", "sounds good",
            "that works", "confirmed", "accurate", "exactly what i need"
        ]
        
        self.role_adherence_phrases = [
            "sorry, i'm the one who needs help"
        ]
        
        self.persona_characteristics = [
            "drowning in work", "systems are getting hammered"
        ]
        
    def _load_mandatory_fields(self) -> Dict[str, str]:
        """Load mandatory fields from the recruiter prompt dynamically"""
        try:
            prompt_path = Path("prompts/recruiter_v1.txt")
            if not prompt_path.exists():
                logger.warning("Recruiter prompt not found, using default fields")
                return self._get_default_mandatory_fields()
            
            with open(prompt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find the mandatory fields section
            mandatory_section = self._extract_mandatory_section(content)
            if not mandatory_section:
                logger.warning("Could not find mandatory fields section, using defaults")
                return self._get_default_mandatory_fields()
            
            # Parse the fields
            fields = self._parse_mandatory_fields(mandatory_section)
            logger.debug(f"Loaded {len(fields)} mandatory fields: {list(fields.keys())}")
            return fields
            
        except Exception as e:
            logger.error(f"Error loading mandatory fields: {e}")
            return self._get_default_mandatory_fields()
    
    def _extract_mandatory_section(self, content: str) -> str:
        """Extract the mandatory fields section from the prompt"""
        # Look for the mandatory fields section
        pattern = r"### 🧱 MANDATORY FIELDS TO EXTRACT.*?(?=###|\Z)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        return match.group(0) if match else ""
    
    def _parse_mandatory_fields(self, section: str) -> Dict[str, str]:
        """Parse mandatory fields from the section text"""
        fields = {}
        lines = section.split('\n')
        
        for line in lines:
            line = line.strip()
            # Skip empty lines, headers, and comments
            if not line or line.startswith('###') or line.startswith('---'):
                continue
            
            # Remove bullet points and extract field name
            field_line = re.sub(r'^[-*]\s*', '', line)
            if '→' in field_line:
                # Handle sub-fields like "If remote/hybrid → Time Zones Allowed"
                field_line = field_line.split('→')[0].strip()
            
            # Clean up field name
            field_name = field_line.replace(':', '').strip()
            if field_name:
                # Map to analysis field names
                analysis_field = self._map_field_to_analysis(field_name)
                fields[analysis_field] = field_name
        
        return fields
    
    def _map_field_to_analysis(self, field_name: str) -> str:
        """Map prompt field names to analysis field names"""
        field_mapping = {
            'Job Title': 'job_title',
            'Workplace Type': 'workplace_type', 
            'Employment Type': 'employment_type',
            'Location': 'location',
            'Seniority Level': 'seniority_level',
            'Education Level': 'education_level',
            'Skills': 'skills',
            'Vacancies': 'vacancies',
            'Languages': 'languages',
            'Responsibilities': 'responsibilities',
            'Application deadline': 'application_deadline',
            'Salary Range': 'salary_range',
            'Recruiter/Contact person': 'recruiter_contact',
            'Internal Notes': 'internal_notes'
        }
        
        # Try exact match first
        if field_name in field_mapping:
            return field_mapping[field_name]
        
        # Try partial matches
        for prompt_field, analysis_field in field_mapping.items():
            if prompt_field.lower() in field_name.lower():
                return analysis_field
        
        # Default to snake_case version
        return field_name.lower().replace(' ', '_').replace('/', '_')
    
    def _get_default_mandatory_fields(self) -> Dict[str, str]:
        """Get default mandatory fields if parsing fails"""
        return {
            'job_title': 'Job Title',
            'workplace_type': 'Workplace Type',
            'employment_type': 'Employment Type', 
            'location': 'Location',
            'seniority_level': 'Seniority Level',
            'skills': 'Skills',
            'responsibilities': 'Responsibilities',
            'salary_range': 'Salary Range'
        }
        
        self.confirmation_phrases = [
            "yes", "looks good", "that's correct", "perfect", "sounds good",
            "that works", "confirmed", "accurate", "exactly what i need"
        ]
        
        self.role_adherence_phrases = [
            "sorry, i'm the one who needs help"
        ]
        
        self.persona_characteristics = [
            "drowning in work", "systems are getting hammered"
        ]
    
    def extract_conversation_summary(self, turns: List[Dict[str, Any]]) -> ConversationSummary:
        """
        Extract a comprehensive summary of the conversation
        
        Args:
            turns: List of conversation turns
            
        Returns:
            ConversationSummary object
        """
        logger.debug(f"Analyzing conversation with {len(turns)} turns")
        
        conversation_flow = []
        key_information_gathered = []
        
        # Extract conversation flow
        for i, turn in enumerate(turns):
            role = turn.get("role", "unknown")
            content = turn.get("content", "")
            
            conversation_flow.append(ConversationTurn(
                turn=i + 1,
                role=role,
                content=content,
                content_preview=content[:100] + "..." if len(content) > 100 else content
            ))
        
        # Extract key information (look for structured data in SUT responses)
        for turn in turns:
            if turn.get("role") == "system":  # SUT responses
                content = turn.get("content", "").lower()
                
                if any(phrase in content for phrase in ["job title:", "salary range:", "experience level:"]):
                    key_information_gathered.append("role_requirements")
                
                if any(phrase in content for phrase in ["location:", "remote"]):
                    key_information_gathered.append("work_location")
                
                if any(phrase in content for phrase in ["skills:", "technologies:"]):
                    key_information_gathered.append("technical_skills")
        
        return ConversationSummary(
            total_turns=len(turns),
            conversation_flow=conversation_flow,
            key_information_gathered=key_information_gathered
        )
    
    def determine_conversation_outcome(self, turns: List[Dict[str, Any]], 
                                    sut_provided_summary: bool, 
                                    proxy_confirmed: bool) -> ConversationOutcome:
        """
        Determine the final outcome of the conversation
        
        Args:
            turns: List of conversation turns
            sut_provided_summary: Whether SUT provided a summary
            proxy_confirmed: Whether proxy confirmed the summary
            
        Returns:
            ConversationOutcome object
        """
        logger.debug(f"Determining outcome - Summary: {sut_provided_summary}, Confirmed: {proxy_confirmed}")
        
        outcome = ConversationOutcome(
            status="incomplete",
            completion_level=0,
            success_indicators=[],
            issues=[]
        )
        
        # Check for successful completion
        if sut_provided_summary and proxy_confirmed:
            outcome.status = "completed_successfully"
            outcome.completion_level = 100
            outcome.success_indicators.extend(["role_summary_provided", "user_confirmed_summary"])
        elif sut_provided_summary:
            outcome.status = "summary_provided_awaiting_confirmation"
            outcome.completion_level = 80
            outcome.success_indicators.append("role_summary_provided")
            outcome.issues.append("user_did_not_confirm")
        else:
            outcome.status = "incomplete"
            outcome.completion_level = 50
            outcome.issues.append("no_role_summary_provided")
        
        # Check for role-playing quality
        for turn in turns:
            if turn.get("role") == "user":  # Proxy responses
                content = turn.get("content", "").lower()
                
                if any(phrase in content for phrase in self.role_adherence_phrases):
                    outcome.success_indicators.append("role_adherence_maintained")
                
                if any(phrase in content for phrase in self.persona_characteristics):
                    outcome.success_indicators.append("persona_characteristics_expressed")
        
        logger.debug(f"Outcome determined: {outcome.status} ({outcome.completion_level}%)")
        return outcome
    
    def extract_information_gathered(self, turns: List[Dict[str, Any]]) -> InformationGathered:
        """
        Extract structured information that was gathered during the conversation
        Uses dynamic field extraction based on mandatory fields from the recruiter prompt
        
        Args:
            turns: List of conversation turns
            
        Returns:
            InformationGathered object
        """
        logger.debug("Extracting information from conversation using dynamic field extraction")
        
        info = InformationGathered()
        
        # Combine all conversation content for analysis
        full_conversation = ""
        for turn in turns:
            content = turn.get("content", "")
            full_conversation += f" {content}"
        
        # Extract information for each mandatory field dynamically
        extracted_fields = self._extract_all_fields(full_conversation)
        
        # Map extracted fields to InformationGathered object
        info.role_type = extracted_fields.get('job_title')
        info.location = extracted_fields.get('location')
        info.employment_type = extracted_fields.get('employment_type')
        info.skills_mentioned = self._parse_skills(extracted_fields.get('skills', ''))
        info.salary_range = extracted_fields.get('salary_range')
        
        # Store additional fields in a flexible way
        info.experience_level = extracted_fields.get('seniority_level')
        
        logger.debug(f"Extracted information: Role={info.role_type}, Location={info.location}, Skills={len(info.skills_mentioned)}")
        logger.debug(f"All extracted fields: {extracted_fields}")
        return info
    
    def _extract_all_fields(self, conversation: str) -> Dict[str, str]:
        """Extract all mandatory fields from conversation text"""
        extracted = {}
        conversation_lower = conversation.lower()
        
        for field_key, field_name in self.mandatory_fields.items():
            extracted[field_key] = self._extract_field_value(field_key, field_name, conversation, conversation_lower)
        
        return extracted
    
    def _extract_field_value(self, field_key: str, field_name: str, conversation: str, conversation_lower: str) -> str:
        """Extract value for a specific field from conversation"""
        
        # Job Title extraction - agnostic to industry
        if field_key == 'job_title':
            return self._extract_job_title(conversation, conversation_lower)
        
        # Location extraction
        elif field_key == 'location':
            return self._extract_location(conversation, conversation_lower)
        
        # Employment Type extraction
        elif field_key == 'employment_type':
            return self._extract_employment_type(conversation, conversation_lower)
        
        # Workplace Type extraction
        elif field_key == 'workplace_type':
            return self._extract_workplace_type(conversation, conversation_lower)
        
        # Seniority Level extraction
        elif field_key == 'seniority_level':
            return self._extract_seniority_level(conversation, conversation_lower)
        
        # Skills extraction
        elif field_key == 'skills':
            return self._extract_skills_text(conversation, conversation_lower)
        
        # Salary Range extraction
        elif field_key == 'salary_range':
            return self._extract_salary_range(conversation, conversation_lower)
        
        # Responsibilities extraction
        elif field_key == 'responsibilities':
            return self._extract_responsibilities(conversation, conversation_lower)
        
        # Default extraction - look for explicit mentions
        else:
            return self._extract_generic_field(field_name, conversation, conversation_lower)
    
    def _extract_job_title(self, conversation: str, conversation_lower: str) -> str:
        """Extract job title - agnostic to industry"""
        # Look for explicit job title mentions
        job_title_patterns = [
            r'(?:job title|position|role|hiring for|looking for|need a|want a)\s*:?\s*([^.!?\n]+)',
            r'(?:is|are|would be|should be)\s+(?:a\s+)?([^.!?\n]+(?:developer|engineer|manager|analyst|specialist|coordinator|director|lead|architect|consultant|designer|marketer|sales|accountant|lawyer|doctor|nurse|teacher|writer|editor|administrator|executive|officer|representative|assistant|clerk|technician|operator|supervisor|coordinator))',
            r'(?:we need|looking for|hiring)\s+(?:a\s+)?([^.!?\n]+(?:developer|engineer|manager|analyst|specialist|coordinator|director|lead|architect|consultant|designer|marketer|sales|accountant|lawyer|doctor|nurse|teacher|writer|editor|administrator|executive|officer|representative|assistant|clerk|technician|operator|supervisor|coordinator))',
        ]
        
        for pattern in job_title_patterns:
            matches = re.findall(pattern, conversation_lower, re.IGNORECASE)
            for match in matches:
                title = match.strip()
                if len(title) > 3 and len(title) < 50:  # Reasonable length
                    return title.title()
        
        return None
    
    def _extract_location(self, conversation: str, conversation_lower: str) -> str:
        """Extract location information"""
        # Common location patterns
        location_patterns = [
            r'(?:in|at|based in|located in|working in)\s+([^.!?\n,]+(?:city|town|state|country|remote|hybrid|onsite))',
            r'(?:remote|hybrid|onsite|on-site)',
            r'(?:san francisco|sf|new york|ny|los angeles|la|chicago|boston|seattle|austin|denver|miami|atlanta|phoenix|dallas|houston|philadelphia|detroit|minneapolis|portland|las vegas|orlando|tampa|nashville|pittsburgh|cleveland|columbus|indianapolis|milwaukee|kansas city|salt lake city|richmond|norfolk|greensboro|raleigh|charlotte|jacksonville|memphis|louisville|birmingham|oklahoma city|tulsa|wichita|omaha|des moines|cedar rapids|davenport|rockford|peoria|springfield|madison|rochester|buffalo|syracuse|albany|utica|binghamton|poughkeepsie|newburgh|kingston|glens falls|watertown|ogdensburg|massena|plattsburgh|burlington|rutland|barre|montpelier|concord|nashua|manchester|portsmouth|dover|rochester|concord|laconia|berlin|claremont|lebanon|keene|dover|portsmouth|exeter|hampton|salem|derry|hudson|londonderry|merrimack|bedford|goffstown|weare|new boston|lyndeborough|mont vernon|amherst|milford|wilton|mason|greenville|new ipswich|jaffrey|peterborough|temple|sharon|dublin|hancock|antrim|bennington|francestown|greenfield|lyndeborough|mont vernon|new boston|wilton|mason|greenville|new ipswich|jaffrey|peterborough|temple|sharon|dublin|hancock|antrim|bennington|francestown|greenfield))',
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, conversation_lower, re.IGNORECASE)
            for match in matches:
                location = match.strip()
                if location and len(location) < 50:
                    return location.title()
        
        return None
    
    def _extract_employment_type(self, conversation: str, conversation_lower: str) -> str:
        """Extract employment type"""
        if 'full-time' in conversation_lower or 'fulltime' in conversation_lower:
            return 'Full-time'
        elif 'part-time' in conversation_lower or 'parttime' in conversation_lower:
            return 'Part-time'
        elif 'contract' in conversation_lower:
            return 'Contract'
        elif 'intern' in conversation_lower or 'internship' in conversation_lower:
            return 'Internship'
        return None
    
    def _extract_workplace_type(self, conversation: str, conversation_lower: str) -> str:
        """Extract workplace type"""
        if 'remote' in conversation_lower:
            return 'Remote'
        elif 'hybrid' in conversation_lower:
            return 'Hybrid'
        elif 'onsite' in conversation_lower or 'on-site' in conversation_lower:
            return 'Onsite'
        return None
    
    def _extract_seniority_level(self, conversation: str, conversation_lower: str) -> str:
        """Extract seniority level"""
        seniority_patterns = [
            r'(?:junior|entry-level|entry level|associate|assistant)',
            r'(?:mid-level|mid level|intermediate|middle)',
            r'(?:senior|sr\.|sr)',
            r'(?:lead|principal|staff|architect)',
            r'(?:director|vp|vice president|executive|chief)'
        ]
        
        for pattern in seniority_patterns:
            if re.search(pattern, conversation_lower, re.IGNORECASE):
                match = re.search(pattern, conversation_lower, re.IGNORECASE)
                return match.group().title()
        
        return None
    
    def _extract_skills_text(self, conversation: str, conversation_lower: str) -> str:
        """Extract skills mentioned in conversation"""
        # Look for skills sections or lists
        skills_patterns = [
            r'(?:skills|technologies|tools|requirements|must have|nice to have)[:\s]+([^.!?\n]+)',
            r'(?:experience with|knowledge of|proficient in|familiar with)[:\s]+([^.!?\n]+)',
        ]
        
        for pattern in skills_patterns:
            matches = re.findall(pattern, conversation_lower, re.IGNORECASE)
            for match in matches:
                skills_text = match.strip()
                if len(skills_text) > 5:
                    return skills_text
        
        return None
    
    def _extract_salary_range(self, conversation: str, conversation_lower: str) -> str:
        """Extract salary range"""
        salary_patterns = [
            r'\$[\d,]+(?:-\$[\d,]+)?',
            r'(?:salary|pay|compensation)[:\s]+([^.!?\n]+)',
            r'(?:budget|range)[:\s]+([^.!?\n]+)',
        ]
        
        for pattern in salary_patterns:
            matches = re.findall(pattern, conversation, re.IGNORECASE)
            for match in matches:
                if '$' in match or 'salary' in match.lower():
                    return match.strip()
        
        return None
    
    def _extract_responsibilities(self, conversation: str, conversation_lower: str) -> str:
        """Extract responsibilities mentioned"""
        resp_patterns = [
            r'(?:responsibilities|duties|tasks|what they will do|role involves)[:\s]+([^.!?\n]+)',
            r'(?:will be responsible for|will handle|will manage)[:\s]+([^.!?\n]+)',
        ]
        
        for pattern in resp_patterns:
            matches = re.findall(pattern, conversation_lower, re.IGNORECASE)
            for match in matches:
                responsibilities = match.strip()
                if len(responsibilities) > 10:
                    return responsibilities
        
        return None
    
    def _extract_generic_field(self, field_name: str, conversation: str, conversation_lower: str) -> str:
        """Extract generic field by looking for explicit mentions"""
        field_lower = field_name.lower()
        
        # Look for explicit field mentions
        patterns = [
            rf'{field_lower}[:\s]+([^.!?\n]+)',
            rf'{field_lower}\s+is\s+([^.!?\n]+)',
            rf'{field_lower}\s+will be\s+([^.!?\n]+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, conversation_lower, re.IGNORECASE)
            for match in matches:
                value = match.strip()
                if len(value) > 2:
                    return value
        
        return None
    
    def _parse_skills(self, skills_text: str) -> List[str]:
        """Parse skills text into individual skills"""
        if not skills_text:
            return []
        
        # Split by common delimiters
        skills = re.split(r'[,;|&]|\band\b', skills_text)
        
        # Clean up each skill
        cleaned_skills = []
        for skill in skills:
            skill = skill.strip()
            if skill and len(skill) > 1:
                cleaned_skills.append(skill.title())
        
        return cleaned_skills
    
    def check_sut_provided_summary(self, sut_reply: str) -> bool:
        """
        Check if SUT provided a summary
        
        Args:
            sut_reply: SUT response text
            
        Returns:
            True if summary was provided
        """
        return any(phrase in sut_reply.lower() for phrase in self.summary_phrases)
    
    def check_proxy_confirmation(self, proxy_reply: str) -> bool:
        """
        Check if proxy confirmed the summary
        
        Args:
            proxy_reply: Proxy response text
            
        Returns:
            True if confirmation was provided
        """
        return any(phrase in proxy_reply.lower() for phrase in self.confirmation_phrases)
    
    def check_clarifying_question(self, proxy_reply: str) -> bool:
        """
        Check if a clarifying question was asked by the proxy
        
        Args:
            proxy_reply: Proxy response text
        
        Returns:
            True if a clarifying question was asked
        """
        return "can you clarify" in proxy_reply.lower()

    def check_tangent_inclusion(self, proxy_reply: str) -> bool:
        """
        Check if a tangent was included in the proxy's response
        
        Args:
            proxy_reply: Proxy response text
        
        Returns:
            True if a tangent was included
        """
        return "by the way" in proxy_reply.lower() or "anyway" in proxy_reply.lower()
