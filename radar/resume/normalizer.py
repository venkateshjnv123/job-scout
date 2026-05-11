"""Skill canonicalization — map aliases to canonical skill names."""

_ALIASES: dict[str, str] = {
    "sb": "Spring Boot",
    "springboot": "Spring Boot",
    "spring boot": "Spring Boot",
    "spring_boot": "Spring Boot",
    "spring-boot": "Spring Boot",
    "java": "Java",
    "kafka": "Kafka",
    "rabbitmq": "RabbitMQ",
    "rabbit mq": "RabbitMQ",
    "rabbit-mq": "RabbitMQ",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "redis": "Redis",
    "aws": "AWS",
    "amazon web services": "AWS",
    "microservices": "Microservices",
    "micro services": "Microservices",
    "micro-services": "Microservices",
    "system design": "System Design",
    "system_design": "System Design",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "docker": "Docker",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
    "elasticsearch": "Elasticsearch",
    "elastic search": "Elasticsearch",
    "es": "Elasticsearch",
    "git": "Git",
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",
    "rest": "REST",
    "restful": "REST",
    "grpc": "gRPC",
    "graphql": "GraphQL",
    "hibernate": "Hibernate",
    "jpa": "JPA",
    "maven": "Maven",
    "gradle": "Gradle",
}


def canonicalize(skill: str) -> str:
    """Return canonical form of a skill name."""
    return _ALIASES.get(skill.lower().strip(), skill.strip())


def dedupe_skills(skills: list[str]) -> list[str]:
    """Canonicalize and deduplicate skill list, preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for s in skills:
        canonical = canonicalize(s)
        if canonical.lower() not in seen:
            seen.add(canonical.lower())
            result.append(canonical)
    return result
