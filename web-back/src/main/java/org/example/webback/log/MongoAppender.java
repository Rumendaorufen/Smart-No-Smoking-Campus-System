package org.example.webback.log;

import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.UnsynchronizedAppenderBase;
import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoClients;
import com.mongodb.client.MongoCollection;
import com.mongodb.client.model.InsertManyOptions;
import org.bson.Document;
import org.slf4j.MDC;

import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.regex.Pattern;

public class MongoAppender extends UnsynchronizedAppenderBase<ILoggingEvent> {

    private static final Pattern PHONE_PATTERN = Pattern.compile("1[3-9]\\d{9}");
    private static final Pattern ID_CARD_PATTERN = Pattern.compile("\\d{17}[\\dXx]");
    private static final Pattern JWT_PATTERN = Pattern.compile("eyJ[a-zA-Z0-9_-]+\\.[a-zA-Z0-9_-]+\\.[a-zA-Z0-9_-]+");

    private String connectionUri = "mongodb://localhost:27017";
    private String databaseName = "smart_campus_logs";
    private String collectionName = "logs";

    private MongoClient mongoClient;
    private MongoCollection<Document> collection;
    private final ArrayBlockingQueue<Document> queue = new ArrayBlockingQueue<>(5000);
    private volatile boolean running = true;
    private Thread worker;

    public void setConnectionUri(String uri) { this.connectionUri = uri; }
    public void setDatabaseName(String db) { this.databaseName = db; }
    public void setCollectionName(String col) { this.collectionName = col; }

    @Override
    public void start() {
        super.start();
        mongoClient = MongoClients.create(connectionUri);
        collection = mongoClient.getDatabase(databaseName).getCollection(collectionName);
        worker = new Thread(this::batchLoop, "mongo-appender");
        worker.setDaemon(true);
        worker.start();
    }

    @Override
    protected void append(ILoggingEvent event) {
        if (!queue.offer(buildDocument(event))) {
            addWarn("Log queue full, dropping message: " + event.getMessage());
        }
    }

    private Document buildDocument(ILoggingEvent event) {
        String message = event.getFormattedMessage();
        message = PHONE_PATTERN.matcher(message).replaceAll("138****1234");
        message = ID_CARD_PATTERN.matcher(message).replaceAll("****************");
        message = JWT_PATTERN.matcher(message).replaceAll("***JWT***");

        Document doc = new Document()
                .append("timestamp", new Date(event.getTimeStamp()))
                .append("level", event.getLevel().toString())
                .append("logger", event.getLoggerName())
                .append("message", message)
                .append("service", resolveService(event.getLoggerName()));

        String traceId = MDC.get("trace_id");
        if (traceId != null) doc.append("trace_id", traceId);

        String userId = MDC.get("user_id");
        if (userId != null && !userId.isEmpty()) doc.append("user_id", userId);

        String endpoint = MDC.get("endpoint");
        if (endpoint != null) doc.append("endpoint", endpoint);

        if (event.getThrowableProxy() != null) {
            doc.append("stack_trace", event.getThrowableProxy().getClassName() + ": "
                    + (event.getThrowableProxy().getMessage() != null ? event.getThrowableProxy().getMessage() : ""));
        }

        return doc;
    }

    private String resolveService(String loggerName) {
        if (loggerName.equals("FrontendLog")) return "web-vue";
        return "web-back";
    }

    private void batchLoop() {
        List<Document> batch = new ArrayList<>();
        while (running) {
            try {
                Document doc = queue.poll(1, TimeUnit.SECONDS);
                if (doc != null) {
                    batch.add(doc);
                    queue.drainTo(batch, 99);
                    flush(batch);
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
        }
        queue.drainTo(batch);
        flush(batch);
    }

    private void flush(List<Document> batch) {
        if (batch.isEmpty()) return;
        try {
            collection.insertMany(new ArrayList<>(batch), new InsertManyOptions().ordered(false));
        } catch (Exception e) {
            addError("MongoAppender batch insert failed", e);
        }
        batch.clear();
    }

    @Override
    public void stop() {
        running = false;
        if (worker != null) {
            worker.interrupt();
            try { worker.join(3000); } catch (InterruptedException ignored) {}
        }
        if (mongoClient != null) mongoClient.close();
        super.stop();
    }
}
