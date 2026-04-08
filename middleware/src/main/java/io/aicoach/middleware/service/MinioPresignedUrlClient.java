package io.aicoach.middleware.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;
import software.amazon.awssdk.services.s3.presigner.model.PresignedPutObjectRequest;
import software.amazon.awssdk.services.s3.presigner.model.PutObjectPresignRequest;

import java.net.URI;
import java.time.Duration;

/**
 * Generates presigned S3/MinIO PUT URLs for direct video upload from Flutter.
 *
 * <p>The presigned URL is valid for {@code minio.presign.ttl-minutes} minutes
 * (default 15).  The object key follows the convention:
 * {@code deliveries/{delivery_id}/video.mp4}.</p>
 */
@Service
public class MinioPresignedUrlClient {

    private final String bucket;
    private final long ttlMinutes;
    private final S3Presigner presigner;

    public MinioPresignedUrlClient(
            @Value("${minio.endpoint:http://minio:9000}") String endpointUrl,
            @Value("${minio.bucket:deliveries}") String bucket,
            @Value("${minio.access-key:minioadmin}") String accessKey,
            @Value("${minio.secret-key:minioadmin}") String secretKey,
            @Value("${minio.presign.ttl-minutes:15}") long ttlMinutes) {

        this.bucket = bucket;
        this.ttlMinutes = ttlMinutes;
        this.presigner = S3Presigner.builder()
                .endpointOverride(URI.create(endpointUrl))
                .credentialsProvider(
                        StaticCredentialsProvider.create(
                                AwsBasicCredentials.create(accessKey, secretKey)))
                .region(Region.US_EAST_1) // MinIO ignores region; SDK requires a value
                .serviceConfiguration(
                        software.amazon.awssdk.services.s3.S3Configuration.builder()
                                .pathStyleAccessEnabled(true) // required for MinIO
                                .build())
                .build();
    }

    /**
     * Generates a presigned PUT URL for the given object key.
     *
     * @param objectKey e.g. {@code deliveries/{delivery_id}/video.mp4}
     * @return a pre-signed HTTPS URL valid for the configured TTL
     */
    public String generatePutUrl(String objectKey) {
        PutObjectRequest putRequest = PutObjectRequest.builder()
                .bucket(bucket)
                .key(objectKey)
                .contentType("video/mp4")
                .build();

        PutObjectPresignRequest presignRequest = PutObjectPresignRequest.builder()
                .signatureDuration(Duration.ofMinutes(ttlMinutes))
                .putObjectRequest(putRequest)
                .build();

        PresignedPutObjectRequest presignedRequest = presigner.presignPutObject(presignRequest);
        return presignedRequest.url().toString();
    }
}
