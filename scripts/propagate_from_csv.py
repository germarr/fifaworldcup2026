#!/usr/bin/env python3
"""
Propagate Tournament Data from CSV
-----------------------------------
This script uses group_stage_matches.csv as the single source of truth
and propagates changes throughout the entire application.

Features:
- Reads teams, groups, and matches from CSV
- Adds/updates/removes teams in the database
- Adds/updates/removes matches in the database
- Regenerates knockout bracket dynamically
- Updates group standings
- Supports dry-run mode to preview changes

Usage:
    python scripts/propagate_from_csv.py                    # Apply changes
    python scripts/propagate_from_csv.py --dry-run          # Preview changes
    python scripts/propagate_from_csv.py --reset            # Full reset and reseed
"""

import sys
import os
import csv
import re
from datetime import datetime, timedelta
from typing import Dict, List, Set, Tuple, Optional

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select, func
from app.database import engine, create_db_and_tables
from app.models import Team, Match, GroupStanding
from app.tournament_config import (
    generate_knockout_bracket_structure,
    get_knockout_placeholders,
    get_all_groups,
    get_qualifying_teams_count
)


class TournamentPropagator:
    """Handles propagation of tournament data from CSV to database."""

    def __init__(self, csv_file: str = 'mockups/group_stage_matches.csv', dry_run: bool = False):
        self.csv_file = csv_file
        self.dry_run = dry_run
        self.stats = {
            'teams_added': 0,
            'teams_updated': 0,
            'teams_removed': 0,
            'matches_added': 0,
            'matches_updated': 0,
            'matches_removed': 0,
            'standings_added': 0,
            'standings_removed': 0,
            'flags_added': 0,
        }

        # Comprehensive country code mapping (ISO 3166-1 alpha-3 to alpha-2)
        self.iso_alpha3_to_alpha2 = {
            # Current teams
            'ARG': 'ar', 'AUS': 'au', 'AUT': 'at', 'BEL': 'be', 'BOL': 'bo',
            'BRA': 'br', 'CAN': 'ca', 'CHE': 'ch', 'CIV': 'ci', 'COL': 'co',
            'CPV': 'cv', 'CUW': 'cw', 'DEN': 'dk', 'DEU': 'de', 'DZA': 'dz',
            'ECU': 'ec', 'EGY': 'eg', 'ENG': 'gb-eng', 'ESP': 'es', 'FRA': 'fr',
            'GHA': 'gh', 'HRV': 'hr', 'HTI': 'ht', 'IRN': 'ir', 'ITA': 'it',
            'JOR': 'jo', 'JPN': 'jp', 'KOR': 'kr', 'MAR': 'ma', 'MEX': 'mx',
            'NCL': 'nc', 'NLD': 'nl', 'NOR': 'no', 'NZL': 'nz', 'PAN': 'pa',
            'PRT': 'pt', 'PRY': 'py', 'QAT': 'qa', 'SAU': 'sa', 'SCO': 'gb-sct',
            'SEN': 'sn', 'TUN': 'tn', 'TUR': 'tr', 'UKR': 'ua', 'URY': 'uy',
            'USA': 'us', 'UZB': 'uz', 'ZAF': 'za',

            # Additional FIFA/common codes
            'CRC': 'cr', 'CRO': 'hr', 'GER': 'de', 'KSA': 'sa', 'NED': 'nl',
            'POL': 'pl', 'POR': 'pt', 'SRB': 'rs', 'SUI': 'ch', 'URU': 'uy',
            'WAL': 'gb-wls', 'CMR': 'cm',

            # Extended list for future teams
            'AFG': 'af', 'ALB': 'al', 'AND': 'ad', 'AGO': 'ao', 'ARM': 'am',
            'AZE': 'az', 'BHR': 'bh', 'BGD': 'bd', 'BLR': 'by', 'BEN': 'bj',
            'BTN': 'bt', 'BIH': 'ba', 'BWA': 'bw', 'BRN': 'bn', 'BGR': 'bg',
            'BFA': 'bf', 'BDI': 'bi', 'KHM': 'kh', 'CMR': 'cm', 'CHN': 'cn',
            'COG': 'cg', 'COD': 'cd', 'CRI': 'cr', 'CYP': 'cy', 'CZE': 'cz',
            'DNK': 'dk', 'DOM': 'do', 'SLV': 'sv', 'ERI': 'er', 'EST': 'ee',
            'ETH': 'et', 'FIN': 'fi', 'GAB': 'ga', 'GMB': 'gm', 'GEO': 'ge',
            'GRC': 'gr', 'GTM': 'gt', 'GIN': 'gn', 'GNB': 'gw', 'GUY': 'gy',
            'HND': 'hn', 'HUN': 'hu', 'ISL': 'is', 'IND': 'in', 'IDN': 'id',
            'IRQ': 'iq', 'IRL': 'ie', 'ISR': 'il', 'JAM': 'jm', 'KAZ': 'kz',
            'KEN': 'ke', 'PRK': 'kp', 'KWT': 'kw', 'KGZ': 'kg', 'LAO': 'la',
            'LVA': 'lv', 'LBN': 'lb', 'LBR': 'lr', 'LBY': 'ly', 'LIE': 'li',
            'LTU': 'lt', 'LUX': 'lu', 'MKD': 'mk', 'MDG': 'mg', 'MWI': 'mw',
            'MYS': 'my', 'MLI': 'ml', 'MLT': 'mt', 'MRT': 'mr', 'MUS': 'mu',
            'MDA': 'md', 'MNG': 'mn', 'MNE': 'me', 'MOZ': 'mz', 'MMR': 'mm',
            'NAM': 'na', 'NPL': 'np', 'NIC': 'ni', 'NER': 'ne', 'NGA': 'ng',
            'NIR': 'gb-nir', 'OMN': 'om', 'PAK': 'pk', 'PSE': 'ps', 'PNG': 'pg',
            'PER': 'pe', 'PHL': 'ph', 'QAT': 'qa', 'ROU': 'ro', 'RUS': 'ru',
            'RWA': 'rw', 'SMR': 'sm', 'STP': 'st', 'SEN': 'sn', 'SRB': 'rs',
            'SLE': 'sl', 'SGP': 'sg', 'SVK': 'sk', 'SVN': 'si', 'SOM': 'so',
            'KOR': 'kr', 'SSD': 'ss', 'LKA': 'lk', 'SDN': 'sd', 'SUR': 'sr',
            'SWE': 'se', 'SYR': 'sy', 'TJK': 'tj', 'TZA': 'tz', 'THA': 'th',
            'TLS': 'tl', 'TGO': 'tg', 'TTO': 'tt', 'TKM': 'tm', 'UGA': 'ug',
            'ARE': 'ae', 'GBR': 'gb', 'VEN': 've', 'VNM': 'vn', 'YEM': 'ye',
            'ZMB': 'zm', 'ZWE': 'zw',
        }

    def extract_teams_from_csv(self) -> Dict[str, Dict]:
        """Extract unique teams from CSV file keyed by team code."""
        teams_map: Dict[str, Dict] = {}

        with open(self.csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Process team1
                team1_code = row['team1_code'].strip()
                team1_name = row['team1_name'].strip()
                group = row['group'].strip()

                if team1_code != 'TBD' and not team1_code.startswith('TB') and team1_code not in teams_map:
                    teams_map[team1_code] = {
                        'name': team1_name,
                        'code': team1_code,
                        'group': group
                    }
                elif team1_code != 'TBD' and not team1_code.startswith('TB') and team1_code in teams_map:
                    existing = teams_map[team1_code]
                    if existing['name'] != team1_name or existing['group'] != group:
                        print(
                            f"⚠️  Duplicate code in CSV: {team1_code} "
                            f"({existing['name']}/{existing['group']} vs {team1_name}/{group})"
                        )

                # Process team2
                team2_code = row['team2_code'].strip()
                team2_name = row['team2_name'].strip()

                if team2_code != 'TBD' and not team2_code.startswith('TB') and team2_code not in teams_map:
                    teams_map[team2_code] = {
                        'name': team2_name,
                        'code': team2_code,
                        'group': group
                    }
                elif team2_code != 'TBD' and not team2_code.startswith('TB') and team2_code in teams_map:
                    existing = teams_map[team2_code]
                    if existing['name'] != team2_name or existing['group'] != group:
                        print(
                            f"⚠️  Duplicate code in CSV: {team2_code} "
                            f"({existing['name']}/{existing['group']} vs {team2_name}/{group})"
                        )

        return teams_map

    def extract_groups_from_csv(self) -> Set[str]:
        """Extract unique group letters from CSV file."""
        groups = set()
        with open(self.csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                group = row['group'].strip()
                if group:
                    groups.add(group)
        return groups

    def extract_matches_from_csv(self) -> List[Dict]:
        """Extract group stage matches from CSV file."""
        matches = []

        with open(self.csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                match_number = int(row['match_number'])
                team1_code = row['team1_code'].strip()
                team2_code = row['team2_code'].strip()
                team1_name = row['team1_name'].strip()
                team2_name = row['team2_name'].strip()

                # Parse date
                date_str = row['date'].strip()
                match_date = datetime.strptime(date_str, '%m/%d/%Y')

                matches.append({
                    'match_number': match_number,
                    'round': row['round'].strip(),
                    'group': row['group'].strip(),
                    'team1_code': team1_code,
                    'team1_name': team1_name,
                    'team2_code': team2_code,
                    'team2_name': team2_name,
                    'match_date': match_date,
                    'stadium': row.get('stadium', '').strip() or None,
                    'time': row.get('time', '').strip() or None,
                    'datetime_str': row.get('datetime', '').strip() or None,
                })

        return matches

    def sync_teams(self, session: Session):
        """Synchronize teams between CSV and database."""
        print("\n" + "="*60)
        print("SYNCHRONIZING TEAMS")
        print("="*60)

        # Get teams from CSV
        csv_teams = self.extract_teams_from_csv()
        csv_team_codes = set(csv_teams.keys())

        # Get teams from database
        db_teams = session.exec(select(Team)).all()
        db_teams_map = {team.code: team for team in db_teams}
        db_team_codes = set(db_teams_map.keys())

        # Find differences
        teams_to_add = csv_team_codes - db_team_codes
        teams_to_remove = db_team_codes - csv_team_codes
        teams_to_check = csv_team_codes & db_team_codes

        # Add new teams
        for team_code, team_data in csv_teams.items():
            if team_code in teams_to_add:
                print(f"➕ ADD: {team_data['name']} ({team_data['code']}) - Group {team_data['group']}")
                if not self.dry_run:
                    new_team = Team(**team_data)
                    session.add(new_team)
                self.stats['teams_added'] += 1

        # Update existing teams (check for group changes or name changes)
        for team_code, team_data in csv_teams.items():
            if team_code in teams_to_check:
                db_team = db_teams_map[team_code]
                changes = []

                if db_team.name != team_data['name']:
                    changes.append(f"name: {db_team.name} → {team_data['name']}")
                if db_team.group != team_data['group']:
                    changes.append(f"group: {db_team.group} → {team_data['group']}")

                if changes:
                    print(f"🔄 UPDATE: {team_data['code']} - {' | '.join(changes)}")
                    if not self.dry_run:
                        db_team.name = team_data['name']
                        db_team.group = team_data['group']
                        session.add(db_team)
                    self.stats['teams_updated'] += 1

        # Remove teams not in CSV
        for code in teams_to_remove:
            db_team = db_teams_map[code]
            print(f"➖ REMOVE: {db_team.name} ({code}) - Group {db_team.group}")
            if not self.dry_run:
                # Remove associated group standings first
                standings = session.exec(
                    select(GroupStanding).where(GroupStanding.team_id == db_team.id)
                ).all()
                for standing in standings:
                    session.delete(standing)
                session.delete(db_team)
            self.stats['teams_removed'] += 1

        if not self.dry_run:
            session.commit()

        print(f"\nTeams: +{self.stats['teams_added']} ~{self.stats['teams_updated']} -{self.stats['teams_removed']}")

    def sync_matches(self, session: Session):
        """Synchronize ALL matches (Group + Knockout) between CSV and database."""
        print("\n" + "="*60)
        print("SYNCHRONIZING ALL MATCHES")
        print("="*60)

        # Get teams map (for ID resolution)
        teams_list = session.exec(select(Team)).all()
        teams_by_code = {team.code: team for team in teams_list}
        teams_by_name = {team.name: team for team in teams_list}

        # Get matches from CSV
        csv_matches = self.extract_matches_from_csv()
        csv_match_numbers = {m['match_number'] for m in csv_matches}

        # Get all matches from database
        db_matches = session.exec(select(Match)).all()
        db_matches_map = {match.match_number: match for match in db_matches}
        db_match_numbers = set(db_matches_map.keys())

        # Find differences
        matches_to_add = csv_match_numbers - db_match_numbers
        matches_to_remove = db_match_numbers - csv_match_numbers
        matches_to_check = csv_match_numbers & db_match_numbers

        # Add new matches
        for csv_match in csv_matches:
            if csv_match['match_number'] in matches_to_add:
                # Resolve team IDs
                team1_id, team1_placeholder = self._resolve_team(
                    csv_match['team1_code'], csv_match['team1_name'],
                    teams_by_code, teams_by_name
                )
                team2_id, team2_placeholder = self._resolve_team(
                    csv_match['team2_code'], csv_match['team2_name'],
                    teams_by_code, teams_by_name
                )

                print(f"➕ ADD: Match #{csv_match['match_number']} ({csv_match['round']}) - {csv_match['team1_code']} vs {csv_match['team2_code']}")

                if not self.dry_run:
                    new_match = Match(
                        round=csv_match['round'],
                        match_number=csv_match['match_number'],
                        team1_id=team1_id,
                        team2_id=team2_id,
                        team1_placeholder=team1_placeholder,
                        team2_placeholder=team2_placeholder,
                        match_date=csv_match['match_date'],
                        stadium=csv_match['stadium'],
                        time=csv_match['time'],
                        datetime_str=csv_match['datetime_str'],
                        is_finished=False
                    )
                    session.add(new_match)
                self.stats['matches_added'] += 1

        # Update existing matches
        for csv_match in csv_matches:
            if csv_match['match_number'] in matches_to_check:
                db_match = db_matches_map[csv_match['match_number']]

                # Resolve team IDs
                team1_id, team1_placeholder = self._resolve_team(
                    csv_match['team1_code'], csv_match['team1_name'],
                    teams_by_code, teams_by_name
                )
                team2_id, team2_placeholder = self._resolve_team(
                    csv_match['team2_code'], csv_match['team2_name'],
                    teams_by_code, teams_by_name
                )

                changes = []
                if db_match.round != csv_match['round']:
                    changes.append(f"round: {db_match.round} -> {csv_match['round']}")
                if db_match.team1_id != team1_id or db_match.team1_placeholder != team1_placeholder:
                    changes.append(f"team1: changed")
                if db_match.team2_id != team2_id or db_match.team2_placeholder != team2_placeholder:
                    changes.append(f"team2: changed")
                if db_match.stadium != csv_match['stadium']:
                    changes.append(f"stadium: {db_match.stadium} → {csv_match['stadium']}")
                if db_match.time != csv_match['time']:
                    changes.append(f"time: {db_match.time} → {csv_match['time']}")
                if db_match.match_date != csv_match['match_date']:
                    changes.append(f"date: {db_match.match_date} → {csv_match['match_date']}")

                if changes:
                    print(f"🔄 UPDATE: Match #{csv_match['match_number']} - {' | '.join(changes)}")
                    if not self.dry_run:
                        db_match.round = csv_match['round']
                        db_match.team1_id = team1_id
                        db_match.team2_id = team2_id
                        db_match.team1_placeholder = team1_placeholder
                        db_match.team2_placeholder = team2_placeholder
                        db_match.stadium = csv_match['stadium']
                        db_match.time = csv_match['time']
                        db_match.datetime_str = csv_match['datetime_str']
                        db_match.match_date = csv_match['match_date']
                        session.add(db_match)
                    self.stats['matches_updated'] += 1

        # Remove matches not in CSV
        for match_number in matches_to_remove:
            db_match = db_matches_map[match_number]
            print(f"➖ REMOVE: Match #{match_number} - {db_match.round}")
            if not self.dry_run:
                session.delete(db_match)
            self.stats['matches_removed'] += 1

        if not self.dry_run:
            session.commit()

        print(f"\nAll Matches: +{self.stats['matches_added']} ~{self.stats['matches_updated']} -{self.stats['matches_removed']}")

    def regenerate_knockout_bracket(self, session: Session):
        """
        DEPRECATED: Knockout bracket is now managed via CSV.
        This method is kept empty to satisfy existing calls or can be removed.
        """
        print("\n" + "="*60)
        print("KNOCKOUT BRACKET")
        print("="*60)
        print("Skipping dynamic regeneration. Knockout matches are now synced from CSV.")

    def sync_group_standings(self, session: Session):
        """Synchronize group standings with teams."""
        print("\n" + "="*60)
        print("SYNCHRONIZING GROUP STANDINGS")
        print("="*60)

        # Get all teams
        teams = session.exec(select(Team)).all()
        teams_with_groups = [t for t in teams if t.group]

        # Get existing standings
        existing_standings = session.exec(select(GroupStanding)).all()
        existing_team_ids = {s.team_id for s in existing_standings}

        # Add missing standings
        for team in teams_with_groups:
            if team.id not in existing_team_ids:
                print(f"➕ ADD: Standing for {team.name} (Group {team.group})")
                if not self.dry_run:
                    standing = GroupStanding(
                        group_letter=team.group,
                        team_id=team.id,
                        played=0,
                        won=0,
                        drawn=0,
                        lost=0,
                        goals_for=0,
                        goals_against=0,
                        goal_difference=0,
                        points=0,
                    )
                    session.add(standing)
                self.stats['standings_added'] += 1

        # Remove standings for teams that no longer exist
        valid_team_ids = {t.id for t in teams}
        for standing in existing_standings:
            if standing.team_id not in valid_team_ids:
                team_info = f"Team ID {standing.team_id}"
                print(f"➖ REMOVE: Standing for {team_info}")
                if not self.dry_run:
                    session.delete(standing)
                self.stats['standings_removed'] += 1

        if not self.dry_run:
            session.commit()

        print(f"\nGroup Standings: +{self.stats['standings_added']} -{self.stats['standings_removed']}")

    def _resolve_team(self, code: str, name: str, teams_by_code: Dict, teams_by_name: Dict) -> Tuple[int, str]:
        """Resolve team to ID or placeholder."""
        if code == 'TBD':
            return None, name

        # Try by code first
        if code in teams_by_code:
            return teams_by_code[code].id, None

        # Try by name
        if name in teams_by_name:
            return teams_by_name[name].id, None

        # Fallback: Use the code as the placeholder (e.g., "1A", "W73")
        return None, code

    def get_country_code_for_team(self, team_code: str) -> Optional[str]:
        """Convert team code to ISO alpha-2 country code for flagcdn.com."""
        return self.iso_alpha3_to_alpha2.get(team_code.upper())

    def update_flags_file(self, session: Session):
        """Update app/flags.py with mappings for all teams in database."""
        print("\n" + "="*60)
        print("UPDATING FLAGS MAPPING")
        print("="*60)

        # Get all teams from database
        teams = session.exec(select(Team).order_by(Team.code)).all()

        # Read current flags.py file
        flags_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'app', 'flags.py'
        )

        if not os.path.exists(flags_file):
            print(f"❌ Error: flags.py not found at {flags_file}")
            return

        with open(flags_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract existing mappings from the file
        existing_mappings = {}
        pattern = r'"([A-Z]{3})"\s*:\s*"([a-z\-]+)"'
        for match in re.finditer(pattern, content):
            existing_mappings[match.group(1)] = match.group(2)

        # Determine which teams need flags added
        teams_needing_flags = []
        for team in teams:
            if team.code not in existing_mappings:
                country_code = self.get_country_code_for_team(team.code)
                if country_code:
                    teams_needing_flags.append((team.code, country_code, team.name))
                    print(f"➕ ADD: {team.code} → {country_code} ({team.name})")
                else:
                    print(f"⚠️  WARNING: No flag mapping found for {team.code} ({team.name})")

        if not teams_needing_flags and not self.dry_run:
            print("\n✅ All teams already have flag mappings!")
            return

        if teams_needing_flags:
            self.stats['flags_added'] = len(teams_needing_flags)

            if not self.dry_run:
                # Build new mappings section
                new_entries = []
                for code, country_code, name in teams_needing_flags:
                    # Add to existing mappings
                    existing_mappings[code] = country_code

                # Rebuild the FIFA_TO_FLAGCDN dictionary
                # Sort entries for better organization
                sorted_entries = sorted(existing_mappings.items())

                # Build the new dictionary content
                dict_lines = ["FIFA_TO_FLAGCDN = {"]

                for i, (code, country_code) in enumerate(sorted_entries):
                    # Try to find team name for comment
                    team = next((t for t in teams if t.code == code), None)
                    comment = f"  # {team.name}" if team else ""

                    comma = "," if i < len(sorted_entries) - 1 else ""
                    dict_lines.append(f'    "{code}": "{country_code}"{comma}{comment}')

                dict_lines.append("}")

                new_dict_content = "\n".join(dict_lines)

                # Replace the dictionary in the file
                # Find the start and end of the dictionary
                dict_start = content.find("FIFA_TO_FLAGCDN = {")
                if dict_start == -1:
                    print("❌ Error: Could not find FIFA_TO_FLAGCDN dictionary in flags.py")
                    return

                # Find the closing brace
                brace_count = 0
                dict_end = dict_start
                for i in range(dict_start, len(content)):
                    if content[i] == '{':
                        brace_count += 1
                    elif content[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            dict_end = i + 1
                            break

                # Build new content
                new_content = content[:dict_start] + new_dict_content + content[dict_end:]

                # Write back to file
                with open(flags_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)

                print(f"\n✅ Updated {flags_file} with {len(teams_needing_flags)} new flag mappings")

        print(f"\nFlags: +{self.stats['flags_added']}")

    def run(self):
        """Run the full propagation process."""
        print("="*60)
        print("TOURNAMENT DATA PROPAGATION FROM CSV")
        print("="*60)
        print(f"Source: {self.csv_file}")
        print(f"Mode: {'DRY RUN (no changes)' if self.dry_run else 'LIVE (applying changes)'}")
        print("="*60)

        if not os.path.exists(self.csv_file):
            print(f"\n❌ Error: CSV file not found: {self.csv_file}")
            return False

        # Ensure database exists
        create_db_and_tables()

        with Session(engine) as session:
            # Step 1: Sync teams
            self.sync_teams(session)

            # Step 2: Update flags mapping
            self.update_flags_file(session)

            # Step 3: Sync matches (Group + Knockout)
            self.sync_matches(session)

            # Step 4: Sync group standings
            self.sync_group_standings(session)

        # Print summary
        print("\n" + "="*60)
        print("PROPAGATION SUMMARY")
        print("="*60)
        print(f"Teams:     +{self.stats['teams_added']:2} ~{self.stats['teams_updated']:2} -{self.stats['teams_removed']:2}")
        print(f"Flags:     +{self.stats['flags_added']:2}")
        print(f"Matches:   +{self.stats['matches_added']:2} ~{self.stats['matches_updated']:2} -{self.stats['matches_removed']:2}")
        print(f"Standings: +{self.stats['standings_added']:2} -{self.stats['standings_removed']:2}")

        if self.dry_run:
            print("\n🔍 DRY RUN MODE - No changes were applied")
            print("Run without --dry-run to apply these changes")
        else:
            print("\n✅ All changes applied successfully!")

        print("="*60)

        # Show final stats
        with Session(engine) as session:
            team_count = session.exec(select(func.count(Team.id))).first()
            match_count = session.exec(select(func.count(Match.id))).first()
            groups = get_all_groups(session)

            print(f"\nFinal Database State:")
            print(f"  Teams:   {team_count}")
            print(f"  Matches: {match_count}")
            print(f"  Groups:  {len(groups)} ({', '.join(groups)})")

        return True


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Propagate tournament data from CSV to database')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Preview changes without applying them')
    parser.add_argument('--reset', action='store_true', help='Full reset: delete database and reseed from CSV')
    parser.add_argument('--csv', default='mockups/group_stage_matches.csv', help='Path to CSV file')

    args = parser.parse_args()

    if args.reset:
        print("\n⚠️  RESET MODE: This will delete the entire database and reseed from CSV")
        response = input("Are you sure? Type 'yes' to confirm: ")
        if response.lower() != 'yes':
            print("Cancelled.")
            return

        # Delete database file
        db_file = 'worldcup.db'
        if os.path.exists(db_file):
            os.remove(db_file)
            print(f"✅ Deleted {db_file}")

        # Run seed script
        from simulations.seed_data import main as seed_main
        seed_main()
        return

    propagator = TournamentPropagator(csv_file=args.csv, dry_run=args.dry_run)
    success = propagator.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
