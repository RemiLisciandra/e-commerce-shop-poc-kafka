FROM confluentinc/cp-kafka-connect:7.6.0

# Debezium MySQL connector — téléchargé depuis Maven Central (+ fiable que confluent-hub)
# Supporte MariaDB 10.x via le connecteur MySQL
RUN mkdir -p /usr/share/java/debezium-connector-mysql && \
    curl -fsSL "https://repo1.maven.org/maven2/io/debezium/debezium-connector-mysql/2.5.4.Final/debezium-connector-mysql-2.5.4.Final-plugin.tar.gz" \
    -o /tmp/debezium-mysql.tar.gz && \
    tar -xzf /tmp/debezium-mysql.tar.gz -C /usr/share/java/ && \
    rm /tmp/debezium-mysql.tar.gz

# Confluent JDBC sink connector
RUN confluent-hub install --no-prompt confluentinc/kafka-connect-jdbc:10.7.6

# PostgreSQL JDBC driver (required by JDBC sink connector)
RUN curl -fsSL https://jdbc.postgresql.org/download/postgresql-42.7.3.jar \
    -o /usr/share/confluent-hub-components/confluentinc-kafka-connect-jdbc/lib/postgresql-42.7.3.jar
