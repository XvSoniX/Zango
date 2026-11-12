# One image per module. Build from the repository root:
#   docker build --build-arg SERVICE=discovery-service --build-arg PORT=8761 -t zango-discovery .
#   docker build --build-arg SERVICE=gateway-service --build-arg PORT=8080 -t zango-gateway .

ARG SERVICE=gateway-service
ARG PORT=8080

FROM eclipse-temurin:24-jdk AS build
ARG SERVICE
WORKDIR /src

COPY mvnw ./
COPY .mvn .mvn
COPY pom.xml ./
COPY discovery-service/pom.xml discovery-service/pom.xml
COPY gateway-service/pom.xml gateway-service/pom.xml

RUN chmod +x mvnw \
    && ./mvnw -B -ntp -pl "${SERVICE}" -am -DskipTests dependency:go-offline

COPY ${SERVICE}/src ${SERVICE}/src

RUN set -eu \
    && ./mvnw -B -ntp -pl "${SERVICE}" -am -DskipTests package \
    && jar="$(find "${SERVICE}/target" -maxdepth 1 -type f -name "${SERVICE}-*.jar" | head -n 1)" \
    && test -n "${jar}" \
    && cp "${jar}" /src/app.jar

FROM eclipse-temurin:24-jre AS runtime
ARG PORT=8080

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 zango \
    && useradd --system --uid 10001 --gid zango --home-dir /app --shell /usr/sbin/nologin zango \
    && mkdir -p /app \
    && chown zango:zango /app

WORKDIR /app
COPY --from=build --chown=zango:zango /src/app.jar /app/app.jar

USER zango
EXPOSE ${PORT}
ENV JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=75.0"
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
