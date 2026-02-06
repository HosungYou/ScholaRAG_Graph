"""
TTO Sample Data Importer

Imports sample PSU TTO (Technology Transfer Office) patent/invention data
into the ScholaRAG_Graph knowledge graph for PoC demonstration.

Creates entities: Invention, Patent, Inventor, Technology, License, Department
Creates relationships: INVENTED_BY, USES_TECHNOLOGY, PATENT_OF, DEVELOPED_IN, LICENSE_OF
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# ============================================================
# Sample TTO Data - Penn State Technology Transfer Office
# ============================================================

SAMPLE_TTO_DATA = [
    {
        "title": "Quantum-Enhanced Sensor for Agricultural Soil Analysis",
        "abstract": "A novel quantum sensing platform that uses nitrogen-vacancy centers in diamond to detect soil nutrient levels with unprecedented precision. Achieves parts-per-billion sensitivity for nitrogen, phosphorus, and potassium. Field-deployable with solar-powered operation.",
        "inventors": ["Dr. Sarah Chen", "Dr. Michael Torres"],
        "filing_date": "2023-01-15",
        "patent_number": "US 11,456,789",
        "technology_areas": ["Quantum Sensing", "Agriculture Technology", "Environmental Monitoring"],
        "status": "granted",
        "department": "Department of Physics",
        "license_status": "licensed",
        "licensee": "AgriQuantum Inc.",
    },
    {
        "title": "AI-Driven Drug Discovery Pipeline for Rare Diseases",
        "abstract": "An integrated AI pipeline combining graph neural networks with molecular dynamics simulations to identify drug candidates for rare diseases. Reduces drug screening time from years to weeks. Validated on 3 rare disease targets with 85% hit rate.",
        "inventors": ["Dr. James Liu", "Dr. Emily Watson", "Dr. Robert Kim"],
        "filing_date": "2023-04-22",
        "patent_number": "US 11,567,890",
        "technology_areas": ["Drug Discovery", "Artificial Intelligence", "Graph Neural Networks", "Computational Biology"],
        "status": "granted",
        "department": "Department of Computer Science and Engineering",
        "license_status": "available",
    },
    {
        "title": "Biodegradable Polymer for Tissue Scaffolding",
        "abstract": "A biocompatible, biodegradable polymer scaffold that promotes cell growth and tissue regeneration. Degrades at a controlled rate matching tissue healing. Successfully tested in bone and cartilage repair animal models with 90% integration rate.",
        "inventors": ["Dr. Maria Rodriguez"],
        "filing_date": "2023-02-10",
        "patent_number": None,
        "technology_areas": ["Biomaterials", "Tissue Engineering", "Regenerative Medicine"],
        "status": "filed",
        "department": "Department of Biomedical Engineering",
        "license_status": "available",
    },
    {
        "title": "Secure Multi-Party Computation Protocol for Healthcare Data",
        "abstract": "A novel secure multi-party computation protocol enabling multiple healthcare institutions to jointly analyze patient data without revealing individual records. Achieves 100x speedup over existing MPC approaches while maintaining differential privacy guarantees.",
        "inventors": ["Dr. David Park", "Dr. Lisa Chang"],
        "filing_date": "2022-11-05",
        "patent_number": "US 11,678,901",
        "technology_areas": ["Cybersecurity", "Privacy-Preserving Computing", "Healthcare IT", "Distributed Systems"],
        "status": "granted",
        "department": "Department of Computer Science and Engineering",
        "license_status": "licensed",
        "licensee": "HealthSecure Technologies",
    },
    {
        "title": "High-Efficiency Perovskite Solar Cell with Self-Healing Properties",
        "abstract": "A perovskite solar cell achieving 28.3% efficiency with built-in self-healing mechanism that repairs degradation from moisture and UV exposure. Maintains 95% efficiency after 1000 hours of accelerated aging. Uses earth-abundant materials for scalable manufacturing.",
        "inventors": ["Dr. Anna Martinez", "Dr. Kevin Zhou"],
        "filing_date": "2023-07-14",
        "patent_number": None,
        "technology_areas": ["Solar Energy", "Materials Science", "Clean Energy", "Nanotechnology"],
        "status": "filed",
        "department": "Department of Materials Science and Engineering",
        "license_status": "available",
    },
    {
        "title": "Autonomous Drone Swarm for Precision Agriculture",
        "abstract": "A coordinated drone swarm system using distributed AI for real-time crop monitoring and targeted treatment application. Reduces pesticide use by 70% and water consumption by 40% compared to traditional methods. Fleet of 20 drones covers 500 acres per day.",
        "inventors": ["Dr. Thomas Anderson", "Dr. Sarah Chen"],
        "filing_date": "2023-05-30",
        "patent_number": "US 11,789,012",
        "technology_areas": ["Autonomous Systems", "Agriculture Technology", "Artificial Intelligence", "Robotics"],
        "status": "granted",
        "department": "Department of Aerospace Engineering",
        "license_status": "available",
    },
    {
        "title": "Blockchain-Based Energy Trading Platform for Smart Grids",
        "abstract": "A decentralized energy trading platform using blockchain smart contracts for peer-to-peer energy exchange in smart grid networks. Enables prosumers to sell excess renewable energy directly to neighbors with battery storage coordination.",
        "inventors": ["Dr. Richard Walker", "Dr. Karen Hall"],
        "filing_date": "2022-12-03",
        "patent_number": "US 11,901,234",
        "technology_areas": ["Smart Grid", "Blockchain", "Energy Management", "Distributed Systems"],
        "status": "granted",
        "department": "Department of Electrical Engineering",
        "license_status": "available",
    },
    {
        "title": "3D Bioprinting Platform for Tissue Engineering",
        "abstract": "A multi-head bioprinting platform capable of printing complex vascularized tissue constructs using patient-derived cells. Layer resolution of 10 micrometers with 95% cell viability post-printing. Successfully demonstrated functional liver and kidney tissue models for drug testing.",
        "inventors": ["Dr. Laura Allen", "Dr. Mark Wright", "Dr. Jennifer Scott"],
        "filing_date": "2023-06-21",
        "patent_number": None,
        "technology_areas": ["Bioprinting", "Tissue Engineering", "Regenerative Medicine", "Medical Devices"],
        "status": "filed",
        "department": "Department of Biomedical Engineering",
        "license_status": "available",
    },
    {
        "title": "Advanced Concrete Mix with Carbon Capture Properties",
        "abstract": "A novel concrete formulation that actively captures atmospheric CO2 during curing and throughout its service life. Achieves carbon-negative status over 50-year lifespan while maintaining structural performance comparable to Portland cement concrete.",
        "inventors": ["Dr. William Green", "Dr. Michelle Adams"],
        "filing_date": "2023-08-09",
        "patent_number": "US 11,012,345",
        "technology_areas": ["Sustainable Construction", "Carbon Capture", "Civil Engineering", "Climate Technology"],
        "status": "granted",
        "department": "Department of Civil and Environmental Engineering",
        "license_status": "licensed",
        "licensee": "GreenBuild Materials Inc.",
    },
    {
        "title": "Neuromorphic Computing Chip for Edge AI Applications",
        "abstract": "A neuromorphic computing chip architecture inspired by biological neural networks, achieving 100x energy efficiency compared to GPU-based inference. Supports spiking neural networks with on-chip learning. Ideal for edge AI applications in robotics, IoT, and autonomous systems.",
        "inventors": ["Dr. Eric Baker", "Dr. Amanda Turner", "Dr. Joshua Collins"],
        "filing_date": "2022-10-18",
        "patent_number": "US 11,123,456",
        "technology_areas": ["Neuromorphic Computing", "Edge AI", "Computer Architecture", "Hardware Acceleration"],
        "status": "granted",
        "department": "Department of Computer Science and Engineering",
        "license_status": "available",
    },
    {
        "title": "Microfluidic Device for Rapid Pathogen Detection",
        "abstract": "A portable microfluidic device that detects bacterial and viral pathogens in clinical samples within 15 minutes. Uses isothermal amplification and fluorescent detection. Sensitivity comparable to PCR with minimal sample preparation. Battery-operated for point-of-care and field use.",
        "inventors": ["Dr. Samantha Phillips", "Dr. Ryan Campbell"],
        "filing_date": "2023-03-28",
        "patent_number": None,
        "technology_areas": ["Medical Diagnostics", "Microfluidics", "Point-of-Care Testing", "Infectious Disease"],
        "status": "filed",
        "department": "Department of Chemical Engineering",
        "license_status": "available",
    },
    {
        "title": "Hybrid Electric Powertrain for Heavy-Duty Trucks",
        "abstract": "A series-parallel hybrid electric powertrain optimized for Class 8 heavy-duty trucks. Achieves 40% fuel savings in regional haul applications with 500-mile range. Regenerative braking system recovers 80% of kinetic energy. Retrofit-compatible with existing truck platforms.",
        "inventors": ["Dr. Charles Evans", "Dr. Melissa Rivera", "Dr. Donald Mitchell"],
        "filing_date": "2022-09-30",
        "patent_number": "US 11,234,890",
        "technology_areas": ["Electric Vehicles", "Transportation", "Powertrain Engineering", "Clean Transportation"],
        "status": "granted",
        "department": "Department of Mechanical Engineering",
        "license_status": "licensed",
        "licensee": "TransportTech Systems LLC",
    },
]


@dataclass
class ImportProgress:
    """Track import progress for WebSocket updates."""

    status: str = "pending"
    progress: float = 0.0
    message: str = ""
    records_processed: int = 0
    records_total: int = 0
    entities_created: int = 0
    relationships_created: int = 0
    errors: list = field(default_factory=list)


class TTOSampleImporter:
    """
    Imports sample PSU TTO patent/invention data into knowledge graph.

    Creates entities for inventions, patents, inventors, technologies, and licenses.
    Builds relationships to demonstrate technology transfer knowledge graph capabilities.
    """

    def __init__(
        self,
        llm_provider=None,
        db_connection=None,
        graph_store=None,
        progress_callback: Optional[Callable[[ImportProgress], None]] = None,
    ):
        self.llm = llm_provider
        self.db = db_connection
        self.graph_store = graph_store
        self.progress_callback = progress_callback
        self.progress = ImportProgress()

    def _update_progress(
        self,
        status: str = None,
        progress: float = None,
        message: str = None,
    ):
        """Update and broadcast progress."""
        if status:
            self.progress.status = status
        if progress is not None:
            self.progress.progress = progress
        if message:
            self.progress.message = message

        if self.progress_callback:
            self.progress_callback(self.progress)

    async def import_sample_data(self, project_name: str = "PSU TTO Demo") -> dict:
        """
        Import sample TTO data into the knowledge graph.

        Args:
            project_name: Name for the project

        Returns:
            Import result with project_id and statistics
        """
        try:
            self._update_progress("initializing", 0.05, "Initializing TTO data import...")

            # Create project
            project_id = str(uuid4())
            logger.info(f"Creating TTO project: {project_name} (ID: {project_id})")

            if self.db:
                await self.db.execute(
                    """
                    INSERT INTO projects (id, name, research_question, source_path)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    project_id,
                    project_name,
                    "Demonstration of Penn State Technology Transfer Office innovation portfolio",
                    "sample_data/tto",
                )

            self.progress.records_total = len(SAMPLE_TTO_DATA)

            # Phase 1: Create entities
            self._update_progress("processing", 0.1, "Creating entities from TTO records...")
            id_mappings = await self._create_entities(project_id, SAMPLE_TTO_DATA)

            # Phase 2: Generate embeddings
            self._update_progress("processing", 0.5, "Generating embeddings...")
            await self._generate_embeddings(id_mappings)

            # Phase 3: Create relationships
            self._update_progress("building_graph", 0.7, "Building relationships...")
            relationships_count = await self._create_relationships(
                project_id, SAMPLE_TTO_DATA, id_mappings
            )

            # Complete
            self._update_progress("completed", 1.0, "TTO data import completed successfully!")

            return {
                "success": True,
                "project_id": project_id,
                "stats": {
                    "records_imported": len(SAMPLE_TTO_DATA),
                    "entities_created": self.progress.entities_created,
                    "relationships_created": relationships_count,
                },
            }

        except Exception as e:
            logger.exception(f"TTO import failed: {e}")
            self._update_progress("failed", 0.0, f"Import failed: {str(e)}")
            self.progress.errors.append(str(e))
            return {"success": False, "error": str(e)}

    async def _create_entities(self, project_id: str, records: list[dict]) -> dict:
        """Create entities from TTO records."""
        if not self.db:
            return {}

        id_mappings = {
            "inventions": {},
            "patents": {},
            "inventors": {},
            "technologies": {},
            "licenses": {},
            "departments": {},
        }

        entities_created = 0

        for i, record in enumerate(records):
            # Create Invention entity
            invention_id = str(uuid4())
            invention_title = record["title"]
            id_mappings["inventions"][invention_title] = invention_id

            try:
                await self.db.execute(
                    """
                    INSERT INTO entities (
                        id, project_id, entity_type, name, properties,
                        is_visualized, definition
                    ) VALUES ($1, $2, $3::entity_type, $4, $5, $6, $7)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    invention_id,
                    project_id,
                    "Invention",
                    invention_title[:500],
                    json.dumps({
                        "filing_date": record.get("filing_date"),
                        "status": record.get("status"),
                        "license_status": record.get("license_status"),
                        "licensee": record.get("licensee"),
                    }),
                    True,
                    record["abstract"][:1000],
                )
                entities_created += 1
            except Exception as e:
                logger.warning(f"Failed to create Invention entity: {e}")

            # Create Patent entity (if patent number exists)
            if record.get("patent_number"):
                patent_id = str(uuid4())
                patent_number = record["patent_number"]
                id_mappings["patents"][patent_number] = patent_id

                try:
                    await self.db.execute(
                        """
                        INSERT INTO entities (
                            id, project_id, entity_type, name, properties,
                            is_visualized, definition
                        ) VALUES ($1, $2, $3::entity_type, $4, $5, $6, $7)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        patent_id,
                        project_id,
                        "Patent",
                        patent_number,
                        json.dumps({
                            "filing_date": record.get("filing_date"),
                            "status": record.get("status"),
                        }),
                        True,
                        f"Patent for: {invention_title[:200]}",
                    )
                    entities_created += 1
                except Exception as e:
                    logger.warning(f"Failed to create Patent entity: {e}")

            # Create Inventor entities (deduplicated)
            for inventor_name in record.get("inventors", []):
                if inventor_name not in id_mappings["inventors"]:
                    inventor_id = str(uuid4())
                    id_mappings["inventors"][inventor_name] = inventor_id

                    try:
                        await self.db.execute(
                            """
                            INSERT INTO entities (
                                id, project_id, entity_type, name, properties,
                                is_visualized
                            ) VALUES ($1, $2, $3::entity_type, $4, $5, $6)
                            ON CONFLICT (id) DO NOTHING
                            """,
                            inventor_id,
                            project_id,
                            "Inventor",
                            inventor_name[:500],
                            json.dumps({"invention_count": 1}),
                            True,
                        )
                        entities_created += 1
                    except Exception as e:
                        logger.warning(f"Failed to create Inventor entity: {e}")

            # Create Technology entities (deduplicated)
            for tech_area in record.get("technology_areas", []):
                if tech_area not in id_mappings["technologies"]:
                    tech_id = str(uuid4())
                    id_mappings["technologies"][tech_area] = tech_id

                    try:
                        await self.db.execute(
                            """
                            INSERT INTO entities (
                                id, project_id, entity_type, name, properties,
                                is_visualized, definition
                            ) VALUES ($1, $2, $3::entity_type, $4, $5, $6, $7)
                            ON CONFLICT (id) DO NOTHING
                            """,
                            tech_id,
                            project_id,
                            "Technology",
                            tech_area[:500],
                            json.dumps({"application_count": 1}),
                            True,
                            f"Technology area: {tech_area}",
                        )
                        entities_created += 1
                    except Exception as e:
                        logger.warning(f"Failed to create Technology entity: {e}")

            # Create Department entity (deduplicated)
            dept_name = record.get("department")
            if dept_name and dept_name not in id_mappings["departments"]:
                dept_id = str(uuid4())
                id_mappings["departments"][dept_name] = dept_id

                try:
                    await self.db.execute(
                        """
                        INSERT INTO entities (
                            id, project_id, entity_type, name, properties,
                            is_visualized, definition
                        ) VALUES ($1, $2, $3::entity_type, $4, $5, $6, $7)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        dept_id,
                        project_id,
                        "Department",
                        dept_name[:500],
                        json.dumps({}),
                        True,
                        f"Penn State {dept_name}",
                    )
                    entities_created += 1
                except Exception as e:
                    logger.warning(f"Failed to create Department entity: {e}")

            # Create License entity (if licensed)
            if record.get("license_status") == "licensed" and record.get("licensee"):
                license_id = str(uuid4())
                id_mappings["licenses"][invention_title] = license_id

                try:
                    await self.db.execute(
                        """
                        INSERT INTO entities (
                            id, project_id, entity_type, name, properties,
                            is_visualized, definition
                        ) VALUES ($1, $2, $3::entity_type, $4, $5, $6, $7)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        license_id,
                        project_id,
                        "License",
                        f"License: {invention_title[:200]}",
                        json.dumps({
                            "licensee": record.get("licensee"),
                            "status": "active",
                        }),
                        True,
                        f"License agreement for {invention_title[:200]}",
                    )
                    entities_created += 1
                except Exception as e:
                    logger.warning(f"Failed to create License entity: {e}")

            self.progress.records_processed = i + 1
            progress = 0.1 + (0.4 * (i + 1) / len(records))
            self._update_progress("processing", progress, f"Processing record {i + 1}/{len(records)}...")

        self.progress.entities_created = entities_created
        logger.info(f"Created {entities_created} entities")

        return id_mappings

    async def _generate_embeddings(self, id_mappings: dict) -> list:
        """Generate embeddings for entities using LLM provider."""
        if not self.llm or not hasattr(self.llm, "get_embeddings"):
            logger.warning("No embedding function available - skipping embedding generation")
            return []

        if not self.db:
            return []

        logger.info("Generating embeddings for entities")

        entity_data = []

        # Get invention entities
        for title, entity_id in id_mappings["inventions"].items():
            try:
                result = await self.db.fetchrow(
                    "SELECT name, definition FROM entities WHERE id = $1", entity_id
                )
                if result:
                    entity_data.append({
                        "id": entity_id,
                        "text": f"{result['name']}: {result['definition'] or ''}",
                    })
            except Exception as e:
                logger.warning(f"Failed to fetch entity for embedding: {e}")

        # Get technology entities
        for tech_area, entity_id in id_mappings["technologies"].items():
            try:
                result = await self.db.fetchrow(
                    "SELECT name, definition FROM entities WHERE id = $1", entity_id
                )
                if result:
                    entity_data.append({
                        "id": entity_id,
                        "text": f"{result['name']}: {result['definition'] or ''}",
                    })
            except Exception as e:
                logger.warning(f"Failed to fetch entity for embedding: {e}")

        # Generate embeddings in batches
        if entity_data:
            texts = [e["text"] for e in entity_data]
            try:
                embeddings = await self.llm.get_embeddings(texts)

                for i, entity in enumerate(entity_data):
                    if i < len(embeddings):
                        try:
                            await self.db.execute(
                                "UPDATE entities SET embedding = $1 WHERE id = $2",
                                embeddings[i],
                                entity["id"],
                            )
                        except Exception as e:
                            logger.warning(f"Failed to store embedding: {e}")

                logger.info(f"Generated {len(embeddings)} embeddings")
            except Exception as e:
                logger.error(f"Failed to generate embeddings: {e}")

        return entity_data

    async def _create_relationships(
        self, project_id: str, records: list[dict], id_mappings: dict
    ) -> int:
        """Create relationships between entities."""
        if not self.db:
            return 0

        relationships_created = 0

        for record in records:
            invention_title = record["title"]
            invention_id = id_mappings["inventions"].get(invention_title)

            if not invention_id:
                continue

            # INVENTED_BY relationships (Invention -> Inventor)
            for inventor_name in record.get("inventors", []):
                inventor_id = id_mappings["inventors"].get(inventor_name)
                if inventor_id:
                    try:
                        await self.db.execute(
                            """
                            INSERT INTO relationships (
                                id, project_id, source_id, target_id,
                                relationship_type, properties, weight
                            ) VALUES ($1, $2, $3, $4, $5::relationship_type, $6, $7)
                            ON CONFLICT (source_id, target_id, relationship_type) DO NOTHING
                            """,
                            str(uuid4()), project_id, invention_id, inventor_id,
                            "INVENTED_BY", json.dumps({}), 1.0,
                        )
                        relationships_created += 1
                    except Exception as e:
                        logger.warning(f"Failed to create INVENTED_BY relationship: {e}")

            # USES_TECHNOLOGY relationships (Invention -> Technology)
            for tech_area in record.get("technology_areas", []):
                tech_id = id_mappings["technologies"].get(tech_area)
                if tech_id:
                    try:
                        await self.db.execute(
                            """
                            INSERT INTO relationships (
                                id, project_id, source_id, target_id,
                                relationship_type, properties, weight
                            ) VALUES ($1, $2, $3, $4, $5::relationship_type, $6, $7)
                            ON CONFLICT (source_id, target_id, relationship_type) DO NOTHING
                            """,
                            str(uuid4()), project_id, invention_id, tech_id,
                            "USES_TECHNOLOGY", json.dumps({}), 0.8,
                        )
                        relationships_created += 1
                    except Exception as e:
                        logger.warning(f"Failed to create USES_TECHNOLOGY relationship: {e}")

            # PATENT_OF relationships (Patent -> Invention)
            if record.get("patent_number"):
                patent_id = id_mappings["patents"].get(record["patent_number"])
                if patent_id:
                    try:
                        await self.db.execute(
                            """
                            INSERT INTO relationships (
                                id, project_id, source_id, target_id,
                                relationship_type, properties, weight
                            ) VALUES ($1, $2, $3, $4, $5::relationship_type, $6, $7)
                            ON CONFLICT (source_id, target_id, relationship_type) DO NOTHING
                            """,
                            str(uuid4()), project_id, patent_id, invention_id,
                            "PATENT_OF", json.dumps({
                                "filing_date": record.get("filing_date"),
                                "status": record.get("status"),
                            }), 1.0,
                        )
                        relationships_created += 1
                    except Exception as e:
                        logger.warning(f"Failed to create PATENT_OF relationship: {e}")

            # DEVELOPED_IN relationships (Invention -> Department)
            dept_name = record.get("department")
            if dept_name:
                dept_id = id_mappings["departments"].get(dept_name)
                if dept_id:
                    try:
                        await self.db.execute(
                            """
                            INSERT INTO relationships (
                                id, project_id, source_id, target_id,
                                relationship_type, properties, weight
                            ) VALUES ($1, $2, $3, $4, $5::relationship_type, $6, $7)
                            ON CONFLICT (source_id, target_id, relationship_type) DO NOTHING
                            """,
                            str(uuid4()), project_id, invention_id, dept_id,
                            "DEVELOPED_IN", json.dumps({}), 0.9,
                        )
                        relationships_created += 1
                    except Exception as e:
                        logger.warning(f"Failed to create DEVELOPED_IN relationship: {e}")

            # LICENSE_OF relationships (License -> Invention)
            if record.get("license_status") == "licensed":
                license_id = id_mappings["licenses"].get(invention_title)
                if license_id:
                    try:
                        await self.db.execute(
                            """
                            INSERT INTO relationships (
                                id, project_id, source_id, target_id,
                                relationship_type, properties, weight
                            ) VALUES ($1, $2, $3, $4, $5::relationship_type, $6, $7)
                            ON CONFLICT (source_id, target_id, relationship_type) DO NOTHING
                            """,
                            str(uuid4()), project_id, license_id, invention_id,
                            "LICENSE_OF", json.dumps({"licensee": record.get("licensee")}), 1.0,
                        )
                        relationships_created += 1
                    except Exception as e:
                        logger.warning(f"Failed to create LICENSE_OF relationship: {e}")

        self.progress.relationships_created = relationships_created
        logger.info(f"Created {relationships_created} relationships")

        return relationships_created
