# ─── Stage 1: Build the Spring Boot JAR ───────────────────────────────────────
FROM eclipse-temurin:25-jdk-noble AS build

WORKDIR /app

# Copy Maven wrapper and POM first for dependency caching
COPY mvnw pom.xml ./
COPY .mvn .mvn
RUN chmod +x mvnw && ./mvnw dependency:go-offline -q

# Copy source and build
COPY src ./src
RUN ./mvnw package -DskipTests -q

# ─── Stage 2: Runtime image with PostgreSQL ────────────────────────────────────
FROM eclipse-temurin:25-jre-noble

# Install PostgreSQL
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql \
    && rm -rf /var/lib/apt/lists/*

# ── PostgreSQL configuration ────────────────────────────────────────────────
ENV POSTGRES_DB=middleware \
    POSTGRES_USER=middleware \
    POSTGRES_PASSWORD=middleware \
    PGDATA=/var/lib/postgresql/data

# ── Spring Boot datasource (points to localhost postgres inside the container)
ENV SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5432/${POSTGRES_DB} \
    SPRING_DATASOURCE_USERNAME=${POSTGRES_USER} \
    SPRING_DATASOURCE_PASSWORD=${POSTGRES_PASSWORD} \
    SPRING_DATASOURCE_DRIVER_CLASS_NAME=org.postgresql.Driver \
    SPRING_JPA_DATABASE_PLATFORM=org.hibernate.dialect.PostgreSQLDialect \
    SPRING_JPA_HIBERNATE_DDL_AUTO=update

WORKDIR /app

COPY --from=build /app/target/middleware-*.jar app.jar
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8080 5432

ENTRYPOINT ["docker-entrypoint.sh"]
