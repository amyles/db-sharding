package oracle.sharding.examples;

import oracle.sharding.details.Chunk;
import oracle.sharding.details.OracleRoutingTable;
import oracle.sharding.splitter.PartitionEngine;
import oracle.sharding.splitter.ThreadBasedPartition;
import oracle.sharding.sql.ShardConfigurationInfo;
import oracle.sharding.tools.UnbatchingSink;

import java.io.BufferedWriter;
import java.io.FileWriter;
import java.io.IOException;
import java.sql.Connection;
import java.sql.DriverManager;
import java.util.List;
import java.util.function.Consumer;
import java.util.stream.Stream;

/**
 * Example of partitioning.
 */
public class GenToFile {
    private static final String connectionString = "jdbc:oracle:thin:@" +
            "(DESCRIPTION=(ADDRESS=(HOST=slc07efe.us.oracle.com)(PORT=1522)(PROTOCOL=tcp))" +
            "(CONNECT_DATA=(SERVICE_NAME=GDS$CATALOG.ORADBCLOUD)))";

    private static final String username = "dyn";
    private static final String password = "123";

    /* Create a function which writes  */
    public Consumer<List<DemoLogEntry>> createOrderSink(String filename) {
        try {
            return UnbatchingSink.unbatchToStrings(new BufferedWriter(new FileWriter(filename)));
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    public void run() throws Exception {
        OracleRoutingTable routingTable;

        /* Create connection to the catalog */
        try (Connection connection = DriverManager.getConnection(connectionString, username, password)) {
            /* Load the routing table from the catalog */
            routingTable = ShardConfigurationInfo.loadFromDatabase(connection).createRoutingTable();
        }

        /* Create a batching partitioning engine based on the catalog */
        PartitionEngine<DemoLogEntry> engine = new ThreadBasedPartition<>(routingTable);

        /* Provide a function, which writes the data for each chunk to a separate file */
        engine.setCreateSinkFunction(
                chunk -> createOrderSink("/tmp/test-CHUNK_" + ((Chunk) chunk).getChunkUniqueId()));

        /* Provide a function, which get the key given an object */
        engine.setKeyFunction(a -> routingTable.createKey(a.getCustomerId()));

        /* Generate a million of demo objects and break  */
        Stream.generate(DemoLogEntry::generate).limit(1000000).parallel()
                .forEach((x) -> engine.getSplitter().feed(x));

        /* Flush all buffers */
        engine.getSplitter().closeAllInputs();

        /* Wait for all writing threads to finish */
        engine.waitAndClose(10240);
    }

    public static void main(String [] args)
    {
        try {
            new GenToFile().run();
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }
}
