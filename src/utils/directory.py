# pyright: reportUnknownMemberType=false

import requests
from lxml import html

from utils.ids import Role


class DirectoryParser:
    BASE_URL: str = "https://directory.andrew.cmu.edu/index.cgi"

    DEPARTMENT_MAPPING: dict[str, list[Role]] = {
        "Architecture": [Role.CFA],
        "Art": [Role.CFA],
        "Arts & Entertainment Management": [Role.CFA, Role.HEINZ],
        "Science and Arts": [Role.BXA, Role.CFA, Role.MCS],
        "Computer Science and Arts": [Role.BXA, Role.CFA, Role.SCS],
        "Engineering Studies and Arts": [Role.BXA, Role.CFA, Role.CIT],
        "Humanities and Arts": [Role.BXA, Role.CFA, Role.DIETRICH],
        "Biological Sciences": [Role.MCS],
        "Biomedical Engineering": [Role.CIT],
        "Business Administration": [Role.TEPPER],
        "CFA Interdisciplinary": [Role.CFA],
        "CIT Interdisciplinary": [Role.CIT],
        "CM Institute for Strategy and Tech": [Role.TEPPER],
        "Chemical Engineering": [Role.CIT],
        "Chemistry": [Role.MCS],
        "Civil & Environmental Engineering": [Role.CIT],
        "Computational Biology": [Role.SCS],
        "Computer Science": [Role.SCS],
        "Design": [Role.CFA],
        "Dietrich College Interdisciplinary": [Role.DIETRICH],
        "Drama": [Role.CFA],
        "Economics": [Role.DIETRICH],
        "Electrical & Computer Engineering": [Role.CIT],
        "Engineering & Public Policy": [Role.CIT],
        "English": [Role.DIETRICH],
        "Entertainment Technology": [Role.CFA],
        "General CIT": [Role.CIT],
        "General Computer Science": [Role.SCS],
        "General Dietrich College": [Role.DIETRICH],
        "General MCS": [Role.MCS],
        "History": [Role.DIETRICH],
        "Human-Computer Interaction": [Role.SCS],
        "Information & Communication Technology": [Role.HEINZ],
        "Information Networking Institute": [Role.CIT],
        "Information Systems Program": [Role.DIETRICH, Role.HEINZ],
        "Information Systems:Sch of IS & Mgt": [Role.DIETRICH, Role.HEINZ],
        "Integrated Innovation Institute": [Role.CIT],
        "Language Technologies Institute": [Role.SCS],
        "Languages Cultures & Appl Linguistics": [Role.DIETRICH],
        "MCS Interdisciplinary": [Role.MCS],
        "Machine Learning": [Role.SCS],
        "Materials Science & Engineering": [Role.CIT],
        "Mathematical Sciences": [Role.MCS],
        "Mechanical Engineering": [Role.CIT],
        "Medical Management:Sch of Pub Pol & Mgt": [Role.HEINZ],
        "Music": [Role.CFA],
        "Neuroscience Institute": [Role.MCS, Role.DIETRICH],
        "Philosophy": [Role.DIETRICH],
        "Physics": [Role.MCS],
        "Psychology": [Role.DIETRICH],
        "Public Management:Sch of Pub Pol & Mgt": [Role.HEINZ],
        "Public Policy & Mgt:Sch of Pub Pol & Mgt": [Role.HEINZ],
        "Health Care Policy:Sch of Pub Pol & Mgt": [Role.HEINZ],
        "Qatar Biological Sciences": [Role.MCS, Role.QATAR],
        "Qatar Business Administration": [Role.TEPPER, Role.QATAR],
        "Qatar Computer Science": [Role.SCS, Role.QATAR],
        "Qatar Information Systems": [Role.DIETRICH, Role.HEINZ, Role.QATAR],
        "Robotics": [Role.SCS],
        "SCS Interdisciplinary": [Role.SCS],
        "Social & Decision Sciences": [Role.DIETRICH],
        "Software & Societal Systems": [Role.SCS],
        "Statistics and Data Science": [Role.DIETRICH],
    }

    LEVEL_MAPPING: dict[str, Role] = {
        "First-Year": Role.FIRST_YEAR,
        "Sophomore": Role.UNDERGRAD,
        "Junior": Role.UNDERGRAD,
        "Senior": Role.UNDERGRAD,
        "Fifth-Year Senior": Role.UNDERGRAD,
        "Masters": Role.GRAD,
        "Doctoral": Role.PHD,
    }

    @classmethod
    async def lookup_user(cls, andrewid: str) -> tuple[list[Role], Role | None]:
        """Look up a user by their Andrew ID and return department roles and class level role."""
        try:
            # make request to CMU directory
            params = {"search": andrewid, "action": "Search"}

            response = requests.get(cls.BASE_URL, params=params, timeout=10)
            response.raise_for_status()

            # parse HTML
            tree = html.fromstring(response.content)

            department_roles = cls._extract_department_roles(tree)
            class_level_role = cls._extract_class_level_role(tree)

            return department_roles, class_level_role

        except Exception as e:
            print(f"Error looking up user {andrewid}: {e}")
            return [], None

    @classmethod
    def _extract_department_roles(cls, tree: html.HtmlElement) -> list[Role]:
        """Extract department roles from the parsed HTML tree."""
        department_roles: list[Role] = []

        # try three XPath selectors for department
        xpath_selectors = [
            '//*[@id="content"]/div/div[3]/text()[1]',
            '//*[@id="content"]/div/div[3]/text()[2]',
            '//*[@id="content"]/div/div[3]/text()[3]',
        ]

        departments: list[str] = []
        for selector in xpath_selectors:
            try:
                result = tree.xpath(selector)
                if result and result[0].strip():
                    departments.append(result[0].strip())
            except Exception:
                continue

        # map departments to roles
        for department in departments:
            if department in cls.DEPARTMENT_MAPPING:
                department_roles.extend(cls.DEPARTMENT_MAPPING[department])

        # remove duplicates while preserving order
        seen: set[Role] = set()
        unique_roles: list[Role] = []

        for role in department_roles:
            if role not in seen:
                seen.add(role)
                unique_roles.append(role)

        return unique_roles

    @classmethod
    def _extract_class_level_role(cls, tree: html.HtmlElement) -> Role | None:
        """Extract class level role from the parsed HTML tree."""
        try:
            # try to get class year
            class_year_xpath = '//*[@id="content"]/div/div[3]/p[2]/text()'
            result = tree.xpath(class_year_xpath)

            if result and result[0].strip():
                class_year = result[0].strip()
                return cls.LEVEL_MAPPING.get(class_year)
            else:
                # no class year found, assume alumni
                return Role.ALUM

        except Exception:
            # if we can't determine class year, assume alumni
            return Role.ALUM
