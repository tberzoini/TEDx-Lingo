import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, collect_list, regexp_replace, struct
from awsglue.dynamicframe import DynamicFrame

args = getResolvedOptions(sys.argv, ["JOB_NAME"])

sc = SparkContext.getOrCreate()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

# --- S3 & MONGODB ATLAS CONFIGURATION ---
S3_BUCKET_RAW = "s3://unibg-tedx-lingo-data-tbgg-raw-v2/"
S3_BUCKET_TRANSCRIPTS = "s3://unibg-tedx-lingo-data-tbgg-transcripts-v2/"
NOME_CONNESSIONE_GLUE = "Mongodbatlas connection"
# ----------------------------------------

# 1. Read and clean raw CSV datasets from S3
final_list = (
    spark.read.option("header", "true")
    .option("quote", '"')
    .option("escape", '"')
    .csv(S3_BUCKET_RAW + "final_list.csv")
)

related_videos = spark.read.option("header", "true").csv(
    S3_BUCKET_RAW + "related_videos.csv"
)

details = (
    spark.read.option("header", "true")
    .option("quote", '"')
    .option("escape", '"')
    .option("multiLine", "true")
    .csv(S3_BUCKET_RAW + "details.csv")
)
details = details.withColumn(
    "description", regexp_replace(col("description"), "\n", " ")
)

trascrizioni = spark.read.option("header", "true").csv(
    S3_BUCKET_TRANSCRIPTS + "trascrizioni (1).csv"
)

# 2. Task A: Watch Next resolution (discard broken links via inner join on slug)
slug_id_map = final_list.select(
    col("slug").alias("slug_lookup"), col("id").alias("correct_id")
)

resolved_videos = related_videos.join(
    slug_id_map,
    related_videos.slug == slug_id_map.slug_lookup,
    "inner",
)

related_agg = resolved_videos.groupBy(col("id").alias("main_talk_id")).agg(
    collect_list(
        struct(col("correct_id").alias("related_id"), col("slug"), col("title"))
    ).alias("watch_next")
)

# 3. Task B: Aggregate timestamped transcript sentences per talk
transcript_agg = trascrizioni.groupBy(col("id").alias("tr_id")).agg(
    collect_list(struct(col("timestamp"), col("sentence"))).alias("transcript_info")
)

# 4. Final join, filter talks with valid transcripts, and rename id -> _id
final_dataset = (
    final_list.join(details, "id", "left")
    .join(related_agg, final_list.id == related_agg.main_talk_id, "left")
    .join(transcript_agg, final_list.id == transcript_agg.tr_id, "left")
    .drop("main_talk_id", "tr_id")
    .filter("transcript_info is not null")
    .withColumnRenamed("id", "_id")
)

# 5. Write curated collection to MongoDB Atlas
dynamic_frame = DynamicFrame.fromDF(final_dataset, glueContext, "dynamic_frame")

write_mongo_options = {
    "connectionName": NOME_CONNESSIONE_GLUE,
    "database": "unibg_tedx_lingo",
    "collection": "talks",
    "ssl": "true",
    "ssl.domain_match": "false",
}

glueContext.write_dynamic_frame.from_options(
    frame=dynamic_frame,
    connection_type="mongodb",
    connection_options=write_mongo_options,
)

job.commit()
