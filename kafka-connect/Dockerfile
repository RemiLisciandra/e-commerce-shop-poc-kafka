FROM confluentinc/cp-kafka-connect:7.6.0

# Debezium MySQL connector (supports MariaDB 10.x)
RUN confluent-hub install --no-prompt debezium/debezium-connector-mysql:2.5.4

# Confluent JDBC sink connector
RUN confluent-hub install --no-prompt confluentinc/kafka-connect-jdbc:10.7.6

# PostgreSQL JDBC driver (required by JDBC sink connector)
RUN curl -fsSL https://jdbc.postgresql.org/download/postgresql-42.7.3.jar \
    -o /usr/share/confluent-hub-components/confluentinc-kafka-connect-jdbc/lib/postgresql-42.7.3.jar
