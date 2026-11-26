package ir.nextminds.admin.config;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.cloud.client.loadbalancer.LoadBalanced;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

import java.net.http.HttpClient;

@Configuration
@EnableConfigurationProperties(AuthClientProperties.class)
public class AuthClientConfig {

    /**
     * Eureka must use a plain builder. The load-balanced builder would treat the
     * Eureka host as a service id.
     */
    @Bean
    @Primary
    RestClient.Builder restClientBuilder() {
        return RestClient.builder();
    }

    @Bean
    @LoadBalanced
    RestClient.Builder authRestClientBuilder(AuthClientProperties properties) {
        HttpClient httpClient = HttpClient.newBuilder()
                .connectTimeout(properties.getConnectTimeout())
                .build();
        JdkClientHttpRequestFactory requestFactory = new JdkClientHttpRequestFactory(httpClient);
        requestFactory.setReadTimeout(properties.getResponseTimeout());
        return RestClient.builder().requestFactory(requestFactory);
    }

    @Bean
    RestClient authRestClient(@LoadBalanced RestClient.Builder authRestClientBuilder, AuthClientProperties properties) {
        return authRestClientBuilder
                .baseUrl(properties.getBaseUrl())
                .build();
    }
}
